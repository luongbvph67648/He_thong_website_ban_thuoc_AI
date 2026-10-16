import { ArrowLeftOutlined } from '@ant-design/icons'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Form, Input, Popconfirm, Result, Space, Spin, Table, Tabs, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { laLoiApi, loiTheoTruong } from '../../../api/loi'
import { NhanTrangThai } from '../../../components/NhanTrangThai'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'
import {
  banDienSan,
  coThayDoi,
  giaTriTuPhienBan,
  kiemTraNoiDung,
  KHOA_QUERY_CHUYEN_MON,
  noiDungRaApi,
  phienBanCoSo,
  TOI_DA_KY_TU,
  TRUONG_VAN_BAN,
  type GiaTriNoiDung,
  type NoiDungSanPham,
  type PhienBanNoiDung,
  type TenTruong,
} from './noiDung'
import { SoSanhPhienBan } from './SoSanhPhienBan'

const ID_TOI_DA = 2_147_483_647 // khớp `IdInt` của backend: ngoài khoảng là 400 chứ không phải 404, nên chặn từ đầu

function docId(gia: string | undefined): number | null {
  if (!gia || !/^[1-9]\d*$/.test(gia)) return null
  const so = Number(gia)
  return Number.isSafeInteger(so) && so <= ID_TOI_DA ? so : null
}

function KhongTimThay() {
  return (
    <Result
      status="404"
      title="Không tìm thấy sản phẩm"
      subTitle="Sản phẩm không tồn tại hoặc đã bị xóa."
      extra={
        <Link to=".." relative="path">
          <Button type="primary">Về danh sách</Button>
        </Link>
      }
    />
  )
}

const THONG_DIEP_XUNG_DOT =
  'Đã có phiên bản mới hơn phiên bản bạn đang soạn (có người vừa lưu hoặc duyệt). Đã tải lại danh sách phiên bản; chữ bạn đang gõ vẫn còn nguyên, hãy xem bản mới ở tab "Phiên bản" rồi lưu lại nếu vẫn cần.'

/** Soạn, xem, duyệt, so sánh các phiên bản nội dung chuyên môn của MỘT sản phẩm (DS10). */
export default function TrangSoanNoiDung() {
  const sanPhamId = docId(useParams().id)
  // Không tự làm mới (focus, kết nối lại): `phien_ban_co_so` phải là số phiên bản người soạn ĐÃ THẤY, nếu không bản
  // mới của người khác bị bỏ qua mà không báo (QĐ-18). Dữ liệu chỉ đổi sau khi mình ghi hoặc gặp 409.
  const chiTiet = useQuery({
    queryKey: [...KHOA_QUERY_CHUYEN_MON, 'san-pham', sanPhamId],
    enabled: sanPhamId !== null,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/chuyen-mon/san-pham/{san_pham_id}', { params: { path: { san_pham_id: sanPhamId! } } })
      if (error) throw error
      return data
    },
    staleTime: Infinity,
    gcTime: 0,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  if (sanPhamId === null || (chiTiet.isError && laLoiApi(chiTiet.error) && chiTiet.error.ma_loi === 'KHONG_TIM_THAY')) return <KhongTimThay />
  if (chiTiet.isError && !chiTiet.data) return <Alert type="error" showIcon title="Không tải được nội dung chuyên môn" />
  if (!chiTiet.data) return <Spin style={{ display: 'block', margin: '48px auto' }} />

  const lamMoi = async (): Promise<NoiDungSanPham | undefined> => {
    const kq = await chiTiet.refetch()
    return kq.isError ? undefined : kq.data
  }
  return <NoiDungView key={sanPhamId} du={chiTiet.data} lamMoi={lamMoi} />
}

function O({ nhan, id, loi, children }: { nhan: string; id: string; loi?: string; children: React.ReactNode }) {
  return (
    <Form.Item label={nhan} htmlFor={id} validateStatus={loi ? 'error' : undefined} help={loi}>
      {children}
    </Form.Item>
  )
}

function NoiDungView({ du, lamMoi }: { du: NoiDungSanPham; lamMoi: () => Promise<NoiDungSanPham | undefined> }) {
  const { message } = App.useApp()
  const quyen = usePhien((s) => s.quyen)
  const coGhi = coQuyen(quyen, 'content.professional.edit')
  const coDuyet = coQuyen(quyen, 'content.approve')

  const [goc, setGoc] = useState<GiaTriNoiDung>(() => giaTriTuPhienBan(banDienSan(du.phien_ban)))
  const [giaTri, setGiaTri] = useState<GiaTriNoiDung>(goc)
  const [daThuLuu, setDaThuLuu] = useState(false)
  const [loiMayChu, setLoiMayChu] = useState<Partial<Record<TenTruong, string>>>({})
  const [thongDiep, setThongDiep] = useState<string | null>(null)
  const [tab, setTab] = useState('soan')

  const loiNhap = daThuLuu ? kiemTraNoiDung(giaTri) : {}
  const loi = { ...loiNhap, ...loiMayChu }
  const doiO = (ten: TenTruong, v: string) => {
    setGiaTri({ ...giaTri, [ten]: v })
    setLoiMayChu(({ [ten]: _bo, ...con }) => con)
  }
  const datLaiTheo = (moi: NoiDungSanPham) => {
    const g = giaTriTuPhienBan(banDienSan(moi.phien_ban))
    setGoc(g)
    setGiaTri(g)
    setDaThuLuu(false)
    setLoiMayChu({})
  }

  const tao = useMutation({
    mutationFn: () =>
      goi(() => api.POST('/api/v1/noi-bo/chuyen-mon/san-pham/{san_pham_id}', { params: { path: { san_pham_id: du.san_pham.id } }, body: noiDungRaApi(giaTri, phienBanCoSo(du.phien_ban)) })),
  })
  const duyet = useMutation({
    mutationFn: (id: number) => goi(() => api.POST('/api/v1/noi-bo/chuyen-mon/{phien_ban_id}/duyet', { params: { path: { phien_ban_id: id } } })),
  })
  const luuTru = useMutation({
    mutationFn: (id: number) => goi(() => api.POST('/api/v1/noi-bo/chuyen-mon/{phien_ban_id}/luu-tru', { params: { path: { phien_ban_id: id } } })),
  })
  const dangBan = tao.isPending || duyet.isPending || luuTru.isPending

  const luu = async () => {
    setThongDiep(null)
    setDaThuLuu(true)
    setLoiMayChu({})
    if (Object.keys(kiemTraNoiDung(giaTri)).length > 0) return setThongDiep('Còn ô chưa hợp lệ, hãy kiểm tra các ô báo đỏ.')
    if (!coThayDoi(giaTri, goc)) return setThongDiep('Chưa có thay đổi nào so với phiên bản hiện có.')
    const kq = await tao.mutateAsync()
    if (!kq.ok) {
      if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') {
        await lamMoi()
        return setThongDiep(THONG_DIEP_XUNG_DOT)
      }
      const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      const trongForm = Object.fromEntries(Object.entries(theoTruong).filter(([k]) => TRUONG_VAN_BAN.some((t) => t.ten === k) || k === 'file_hdsd_url'))
      setLoiMayChu(trongForm)
      return setThongDiep(Object.keys(theoTruong).length > 0 ? 'Máy chủ từ chối nội dung, hãy xem các ô báo đỏ.' : thongDiepChung(kq.loi))
    }
    void message.success(`Đã lưu bản nháp ${kq.data.phien_ban}`)
    const moi = await lamMoi()
    if (moi) datLaiTheo(moi)
    setTab('phien-ban')
  }

  const thaoTac = async (kieu: 'duyet' | 'luu_tru', p: PhienBanNoiDung) => {
    setThongDiep(null)
    const kq = await (kieu === 'duyet' ? duyet : luuTru).mutateAsync(p.id)
    if (!kq.ok) {
      const xungDot = kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI'
      void message.error(xungDot ? kq.loi!.thong_diep : thongDiepChung(kq.loi))
      if (xungDot) await lamMoi()
      return
    }
    void message.success(kieu === 'duyet' ? `Đã duyệt bản ${p.phien_ban}, nội dung đang hiển thị cho khách` : `Đã bỏ bản nháp ${p.phien_ban}`)
    await lamMoi()
  }

  const cot: ColumnsType<PhienBanNoiDung> = [
    { title: 'Bản', dataIndex: 'phien_ban', key: 'so', width: 70 },
    { title: 'Trạng thái', key: 'trang_thai', render: (_, p) => <NhanTrangThai loai="noi_dung" giaTri={p.trang_thai} /> },
    { title: 'Người soạn', key: 'soan', render: (_, p) => p.nguoi_soan?.ho_ten ?? '—' },
    { title: 'Soạn lúc', key: 'luc', render: (_, p) => dinhDangNgay(p.created_at, 'ngayGio') },
    {
      title: 'Duyệt',
      key: 'duyet',
      render: (_, p) => (p.duoc_si_duyet ? `${p.duoc_si_duyet.ho_ten} · ${dinhDangNgay(p.ngay_duyet, 'ngayGio')}` : '—'),
    },
    {
      title: 'Thao tác',
      key: 'tt',
      render: (_, p) =>
        p.trang_thai === 'nhap' ? (
          <Space>
            <YeuCauQuyen ma="content.approve" kieu="nut">
              <Popconfirm title={`Duyệt bản ${p.phien_ban}?`} description="Nội dung này sẽ hiển thị cho khách; bản đang hiển thị chuyển sang lưu trữ." okText="Duyệt" cancelText="Hủy" onConfirm={() => thaoTac('duyet', p)}>
                <Button size="small" type="primary" disabled={dangBan}>
                  Duyệt
                </Button>
              </Popconfirm>
            </YeuCauQuyen>
            <YeuCauQuyen ma="content.professional.edit" kieu="nut">
              <Popconfirm title={`Bỏ bản nháp ${p.phien_ban}?`} okText="Bỏ bản nháp" cancelText="Hủy" okButtonProps={{ danger: true }} onConfirm={() => thaoTac('luu_tru', p)}>
                <Button size="small" danger disabled={dangBan}>
                  Bỏ bản nháp
                </Button>
              </Popconfirm>
            </YeuCauQuyen>
          </Space>
        ) : null,
    },
  ]

  return (
    <div>
      <Link to=".." relative="path">
        <Button type="link" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0 }}>
          Danh sách sản phẩm
        </Button>
      </Link>
      <Typography.Title level={3} style={{ marginTop: 0 }}>
        {du.san_pham.ten}
      </Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <code>{du.san_pham.sku}</code>
        <NhanTrangThai loai="loai_san_pham" giaTri={du.san_pham.loai_san_pham} />
        {du.phien_ban_hien_thi === null ? <Typography.Text type="secondary">Chưa có nội dung nào được duyệt: khách chưa thấy phần chuyên môn.</Typography.Text> : <Typography.Text>Đang hiển thị bản {du.phien_ban_hien_thi}.</Typography.Text>}
      </Space>
      <Tabs
        activeKey={tab}
        onChange={setTab}
        items={[
          {
            key: 'soan',
            label: 'Soạn bản mới',
            children: (
              <Space orientation="vertical" size={16} style={{ width: '100%' }}>
                <Alert type="info" showIcon title="Mỗi lần lưu tạo một bản nháp mới (bản cũ không bị sửa); chỉ bản được duyệt mới hiển thị cho khách và được AI dùng." />
                {thongDiep && <Alert type="error" showIcon title={thongDiep} />}
                <Form layout="vertical" component="div" disabled={!coGhi || dangBan}>
                  {TRUONG_VAN_BAN.map((t) => (
                    <O key={t.ten} nhan={t.nhan} id={`cm-${t.ten}`} loi={loi[t.ten]}>
                      <Input.TextArea id={`cm-${t.ten}`} value={giaTri[t.ten]} autoSize={{ minRows: 3, maxRows: 14 }} maxLength={TOI_DA_KY_TU * 2} status={loi[t.ten] ? 'error' : undefined} onChange={(e) => doiO(t.ten, e.target.value)} />
                    </O>
                  ))}
                  <O nhan="Tờ hướng dẫn sử dụng gốc (đường dẫn)" id="cm-file_hdsd_url" loi={loi.file_hdsd_url}>
                    <Input id="cm-file_hdsd_url" value={giaTri.file_hdsd_url} autoComplete="off" status={loi.file_hdsd_url ? 'error' : undefined} onChange={(e) => doiO('file_hdsd_url', e.target.value)} />
                  </O>
                </Form>
                <YeuCauQuyen ma="content.professional.edit" kieu="nut">
                  <Button type="primary" loading={tao.isPending} disabled={dangBan} onClick={() => void luu()}>
                    Lưu thành bản nháp mới
                  </Button>
                </YeuCauQuyen>
              </Space>
            ),
          },
          {
            key: 'phien-ban',
            label: `Phiên bản (${du.phien_ban.length})`,
            children: <Table<PhienBanNoiDung> rowKey="id" size="small" columns={cot} dataSource={du.phien_ban} pagination={false} locale={{ emptyText: 'Chưa có phiên bản nào' }} />,
          },
          { key: 'so-sanh', label: 'So sánh', children: <SoSanhPhienBan cac={du.phien_ban} /> },
        ]}
      />
      {!coDuyet && coGhi && <Typography.Text type="secondary">Bạn soạn được nhưng không có quyền duyệt.</Typography.Text>}
    </div>
  )
}
