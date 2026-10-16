import { CopyOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Checkbox, Descriptions, Empty, Image, Input, InputNumber, Modal, Result, Select, Space, Spin, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'

type YeuCau = components['schemas']['YeuCauDuyetRa']
type SanPham = components['schemas']['SanPhamChon']
type CanhBao = components['schemas']['CanhBaoRa']
type Checklist = components['schemas']['ChecklistVao']
type TaoDonRa = components['schemas']['TaoDonRa']

interface DongChon {
  san_pham_id: number
  don_vi_id: number
  so_luong: number
  ten: string
  ten_don_vi: string
  gia: string
  ke_don: boolean
}

const MUC = { chong_chi_dinh: ['red', 'Chống chỉ định'], nghiem_trong: ['volcano', 'Nghiêm trọng'], trung_binh: ['orange', 'Trung bình'], nhe: ['blue', 'Nhẹ'] } as const
const CHECKLIST: [keyof Checklist, string][] = [
  ['thong_tin_nguoi_benh', 'Có thông tin người bệnh (họ tên, tuổi/năm sinh, địa chỉ)'],
  ['thong_tin_bac_si', 'Có thông tin bác sĩ (họ tên, chữ ký, cơ sở khám)'],
  ['ngay_ke_trong_hieu_luc', 'Ngày kê còn trong hiệu lực'],
  ['don_chua_su_dung', 'Đơn chưa được sử dụng'],
  ['da_kiem_tra_tuong_tac', 'Đã xem cảnh báo tương tác và dị ứng'],
]
const RONG: Checklist = { thong_tin_nguoi_benh: false, thong_tin_bac_si: false, ngay_ke_trong_hieu_luc: false, don_chua_su_dung: false, da_kiem_tra_tuong_tac: false }

/** DS04, DS05: màn duyệt đơn thuốc. Ảnh đơn, hồ sơ dị ứng (qua hàm cổng ở máy chủ), cảnh báo, checklist, chọn thuốc, tạo đơn. */
export default function TrangDuyetDonThuoc() {
  const { id = '' } = useParams()
  const ycId = Number(id)
  const { message } = App.useApp()
  const dieuHuong = useNavigate()
  const qc = useQueryClient()
  const [dong, setDong] = useState<DongChon[]>([])
  const [tuKhoa, setTuKhoa] = useState('')
  const [tim, setTim] = useState('')
  const [canhBao, setCanhBao] = useState<CanhBao | null>(null)
  const [checklist, setChecklist] = useState<Checklist>(RONG)
  const [ghiChu, setGhiChu] = useState('')
  const [xacNhanTrung, setXacNhanTrung] = useState(false)
  const [dangGui, setDangGui] = useState(false)
  const [moTuChoi, setMoTuChoi] = useState(false)
  const [lyDo, setLyDo] = useState('')
  const [ketQua, setKetQua] = useState<TaoDonRa | null>(null)

  const yc = useQuery({
    queryKey: ['noi-bo', 'don-thuoc', ycId],
    enabled: Number.isInteger(ycId) && ycId > 0,
    retry: false,
    gcTime: 0, // URL ảnh ký có hạn
    queryFn: async () => {
      const r = await goi(() => api.GET('/api/v1/noi-bo/don-thuoc/{yc_id}', { params: { path: { yc_id: ycId } } }))
      if (!r.ok) throw r.loi ?? new Error('Không tải được yêu cầu')
      return r.data as YeuCau
    },
  })
  const goiY = useQuery({
    queryKey: ['noi-bo', 'don-thuoc', ycId, 'san-pham', tim],
    enabled: yc.isSuccess && tim.trim().length >= 2,
    queryFn: async () =>
      (await api.GET('/api/v1/noi-bo/don-thuoc/{yc_id}/san-pham', { params: { path: { yc_id: ycId }, query: { q: tim.trim() } } })).data ?? [],
  })

  useEffect(() => {
    const t = setTimeout(() => setTim(tuKhoa), 300)
    return () => clearTimeout(t)
  }, [tuKhoa])

  useEffect(() => {
    if (!yc.isSuccess || dong.length === 0) return
    let huy = false
    void goi(() =>
      api.POST('/api/v1/noi-bo/don-thuoc/{yc_id}/canh-bao', {
        params: { path: { yc_id: ycId } },
        body: { dong: dong.map((d) => ({ san_pham_id: d.san_pham_id, don_vi_id: d.don_vi_id, so_luong: d.so_luong })) },
      }),
    ).then((r) => {
      if (!huy && r.ok) setCanhBao(r.data)
    })
    return () => {
      huy = true
    }
  }, [dong, yc.isSuccess, ycId])

  if (yc.isLoading) return <Spin />
  if (ketQua)
    return (
      <Result
        status="success"
        title={`Đã tạo đơn ${ketQua.don.ma_don}`}
        subTitle="Hàng đang được giữ đến hạn khách xác nhận."
        extra={[
          ketQua.lien_ket_xac_nhan && (
            <Space key="lk" orientation="vertical">
              <Typography.Text>Link xác nhận đã gửi SMS cho khách (có thể đọc cho khách):</Typography.Text>
              <Typography.Text code copyable={{ icon: <CopyOutlined /> }}>{ketQua.lien_ket_xac_nhan}</Typography.Text>
            </Space>
          ),
          <Button key="ve" type="primary" onClick={() => dieuHuong('/nhan-vien/don-thuoc')}>Về hàng chờ</Button>,
        ]}
      />
    )
  if (yc.isError || !yc.data) {
    const khongKhoa = (yc.error as { ma_loi?: string } | null)?.ma_loi === 'KHONG_CO_QUYEN'
    return (
      <Result
        status={khongKhoa ? 'warning' : '404'}
        title={khongKhoa ? 'Yêu cầu này không đang khóa cho bạn' : 'Không tìm thấy yêu cầu'}
        subTitle={khongKhoa ? 'Hãy nhận xử lý từ hàng chờ (có thể đã quá thời gian khóa và bị nhả).' : undefined}
        extra={<Link to="/nhan-vien/don-thuoc"><Button type="primary">Về hàng chờ</Button></Link>}
      />
    )
  }
  const d = yc.data
  const dongDung = d.trung_anh.filter((t) => t.da_su_dung)
  const thieu = CHECKLIST.filter(([k]) => !checklist[k])
  const canhBaoHienTai = dong.length > 0 ? canhBao : null
  const canGhiChu = canhBaoHienTai?.can_ghi_chu_tu_van ?? false
  const khongGui =
    dong.length === 0 || thieu.length > 0 || (canGhiChu && !ghiChu.trim()) || (dongDung.length > 0 && !xacNhanTrung)

  function them(sp: SanPham, donViId: number, soLuong: number) {
    const dv = sp.don_vi.find((x) => x.id === donViId)
    if (!dv) return
    setDong((ds) => {
      const i = ds.findIndex((x) => x.san_pham_id === sp.id && x.don_vi_id === dv.id)
      if (i >= 0) return ds.map((x, k) => (k === i ? { ...x, so_luong: x.so_luong + soLuong } : x))
      return [...ds, { san_pham_id: sp.id, don_vi_id: dv.id, so_luong: soLuong, ten: sp.ten, ten_don_vi: dv.ten_don_vi, gia: dv.gia_ban, ke_don: sp.loai_san_pham === 'thuoc_ke_don' }]
    })
    setTuKhoa('')
  }

  async function taoDon() {
    setDangGui(true)
    const r = await goi(() =>
      api.POST('/api/v1/noi-bo/don-thuoc/{yc_id}/tao-don', {
        params: { path: { yc_id: ycId } },
        body: {
          dong: dong.map((x) => ({ san_pham_id: x.san_pham_id, don_vi_id: x.don_vi_id, so_luong: x.so_luong })),
          checklist,
          ghi_chu_tu_van: ghiChu.trim() || null,
          xac_nhan_trung_anh: xacNhanTrung,
        },
      }),
    )
    setDangGui(false)
    if (r.ok) return setKetQua(r.data)
    void message.error(thongDiepChung(r.loi))
  }

  async function tuChoi() {
    const r = await goi(() => api.POST('/api/v1/noi-bo/don-thuoc/{yc_id}/tu-choi', { params: { path: { yc_id: ycId } }, body: { ly_do: lyDo.trim() } }))
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    void message.success('Đã từ chối yêu cầu')
    void qc.invalidateQueries({ queryKey: ['noi-bo', 'don-thuoc'] })
    dieuHuong('/nhan-vien/don-thuoc')
  }

  async function nha() {
    const r = await goi(() => api.POST('/api/v1/noi-bo/don-thuoc/{yc_id}/nha', { params: { path: { yc_id: ycId } } }))
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    void qc.invalidateQueries({ queryKey: ['noi-bo', 'don-thuoc'] })
    dieuHuong('/nhan-vien/don-thuoc')
  }

  const hs = d.ho_so_suc_khoe
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Typography.Title level={2} style={{ margin: 0 }}>Duyệt đơn thuốc {d.ma_yeu_cau}</Typography.Title>
        {d.het_khoa_luc && <Tag color="gold">Khóa đến {dinhDangNgay(d.het_khoa_luc, 'ngayGio')}</Tag>}
        <Button onClick={() => void nha()}>Trả về hàng chờ</Button>
      </Space>
      <Descriptions
        bordered
        size="small"
        column={2}
        items={[
          { key: 'ten', label: 'Người bệnh', children: d.ho_ten },
          { key: 'sdt', label: 'SĐT', children: d.so_dien_thoai },
          { key: 'loai', label: 'Khách', children: d.la_thanh_vien ? 'Thành viên' : 'Vãng lai' },
          { key: 'gc', label: 'Ghi chú của khách', children: d.ghi_chu ?? '—' },
        ]}
      />
      <Card size="small" title="Ảnh đơn thuốc">
        <Image.PreviewGroup>
          <Space wrap>{d.anh.map((u) => <Image key={u} src={u} width={200} alt="Ảnh đơn thuốc" />)}</Space>
        </Image.PreviewGroup>
      </Card>
      {d.trung_anh.length > 0 && (
        <Alert
          type={dongDung.length > 0 ? 'error' : 'warning'}
          showIcon
          title={dongDung.length > 0 ? 'Ảnh trùng với đơn đã được sử dụng' : 'Ảnh trùng với yêu cầu khác'}
          description={d.trung_anh.map((t) => `${t.ma_yeu_cau}${t.da_su_dung ? ' (đã dùng)' : ''}`).join(', ')}
        />
      )}
      <Card size="small" title="Hồ sơ sức khỏe của khách">
        {hs ? (
          <Descriptions
            size="small"
            column={1}
            items={[
              { key: 'ns', label: 'Năm sinh', children: hs.nam_sinh ?? '—' },
              { key: 'bn', label: 'Bệnh nền', children: hs.benh_nen ?? '—' },
              { key: 'mt', label: 'Mang thai / cho con bú', children: [hs.dang_mang_thai && 'Mang thai', hs.dang_cho_con_bu && 'Cho con bú'].filter(Boolean).join(', ') || 'Không' },
              { key: 'du', label: 'Dị ứng', children: hs.di_ung.length ? hs.di_ung.map((x) => x.ten_hoat_chat).join(', ') : 'Không khai' },
            ]}
          />
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Khách vãng lai hoặc chưa đồng ý chia sẻ hồ sơ sức khỏe" />
        )}
      </Card>
      {d.thuoc_tren_don.length > 0 && (
        <Card size="small" title="Thuốc trên đơn (AI đọc, chỉ để tham khảo)">
          <Table
            size="small"
            pagination={false}
            rowKey={(r) => `${r.ten_thuoc_tren_don}-${r.ham_luong ?? ''}`}
            dataSource={d.thuoc_tren_don}
            columns={[
              { title: 'Thuốc', dataIndex: 'ten_thuoc_tren_don' },
              { title: 'Hàm lượng', dataIndex: 'ham_luong' },
              { title: 'SL kê', dataIndex: 'so_luong_ke' },
              { title: 'Độ tin cậy', dataIndex: 'do_tin_cay_ai' },
            ]}
          />
        </Card>
      )}
      <Card size="small" title="Chọn sản phẩm cho đơn">
        <Input.Search allowClear placeholder="Tìm theo tên thuốc hoặc hoạt chất" value={tuKhoa} onChange={(e) => setTuKhoa(e.target.value)} />
        <Space orientation="vertical" style={{ width: '100%', marginTop: 8 }}>
          {(goiY.data ?? []).map((sp) => (
            <GoiY key={sp.id} sp={sp} them={them} />
          ))}
        </Space>
        <Table<DongChon>
          style={{ marginTop: 12 }}
          size="small"
          pagination={false}
          rowKey={(r) => `${r.san_pham_id}-${r.don_vi_id}`}
          dataSource={dong}
          locale={{ emptyText: 'Chưa chọn sản phẩm nào' }}
          columns={[
            { title: 'Sản phẩm', render: (_, r) => <>{r.ten} {r.ke_don && <Tag color="red">Kê đơn</Tag>}</> },
            { title: 'Đơn vị', dataIndex: 'ten_don_vi' },
            { title: 'Đơn giá', render: (_, r) => dinhDangTien(r.gia) },
            {
              title: 'SL',
              render: (_, r) => (
                <InputNumber min={1} max={9999} value={r.so_luong} onChange={(v) => setDong((ds) => ds.map((x) => (x === r ? { ...x, so_luong: v ?? 1 } : x)))} />
              ),
            },
            { title: '', render: (_, r) => <Button size="small" danger onClick={() => setDong((ds) => ds.filter((x) => x !== r))}>Bỏ</Button> },
          ]}
        />
      </Card>
      {canhBaoHienTai && (canhBaoHienTai.tuong_tac.length > 0 || canhBaoHienTai.di_ung.length > 0) && (
        <Card size="small" title="Cảnh báo tương tác và dị ứng">
          <Space orientation="vertical" style={{ width: '100%' }}>
            {canhBaoHienTai.di_ung.map((c) => (
              <Alert key={`${c.san_pham_id}-${c.hoat_chat_id}`} type="error" showIcon title={`${c.ten_san_pham} chứa ${c.ten_hoat_chat}: khách khai dị ứng`} />
            ))}
            {canhBaoHienTai.tuong_tac.map((c) => (
              <Alert
                key={`${c.san_pham_a_id}-${c.san_pham_b_id}-${c.hoat_chat_a_id}-${c.hoat_chat_b_id}`}
                type={c.muc_do === 'chong_chi_dinh' || c.muc_do === 'nghiem_trong' ? 'error' : 'warning'}
                showIcon
                title={<><Tag color={MUC[c.muc_do][0]}>{MUC[c.muc_do][1]}</Tag>{c.ten_hoat_chat_a} + {c.ten_hoat_chat_b}</>}
                description={c.khuyen_cao}
              />
            ))}
          </Space>
        </Card>
      )}
      <Card size="small" title="Checklist trước khi tạo đơn">
        <Space orientation="vertical">
          {CHECKLIST.map(([k, nhan]) => (
            <Checkbox key={k} checked={checklist[k]} onChange={(e) => setChecklist((c) => ({ ...c, [k]: e.target.checked }))}>{nhan}</Checkbox>
          ))}
          {dongDung.length > 0 && (
            <Checkbox checked={xacNhanTrung} onChange={(e) => setXacNhanTrung(e.target.checked)}>Tôi đã kiểm tra ảnh trùng và vẫn chấp nhận đơn này</Checkbox>
          )}
        </Space>
        <Input.TextArea
          style={{ marginTop: 12 }}
          rows={3}
          maxLength={500}
          showCount
          value={ghiChu}
          onChange={(e) => setGhiChu(e.target.value)}
          status={canGhiChu && !ghiChu.trim() ? 'error' : undefined}
          placeholder={canGhiChu ? 'Bắt buộc: ghi chú tư vấn cho cảnh báo nghiêm trọng' : 'Ghi chú tư vấn cho khách (không bắt buộc)'}
        />
      </Card>
      <Space>
        <Button type="primary" disabled={khongGui} loading={dangGui} onClick={() => void taoDon()}>Tạo đơn gửi khách</Button>
        <Button danger onClick={() => setMoTuChoi(true)}>Từ chối yêu cầu</Button>
      </Space>
      <Modal
        title="Từ chối yêu cầu đơn thuốc"
        open={moTuChoi}
        okText="Từ chối"
        okButtonProps={{ danger: true, disabled: lyDo.trim().length < 3 }}
        cancelText="Đóng"
        onOk={() => void tuChoi()}
        onCancel={() => setMoTuChoi(false)}
        destroyOnHidden
      >
        <Input.TextArea rows={3} maxLength={500} placeholder="Lý do (bắt buộc, khách sẽ nhận được)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
      </Modal>
    </Space>
  )
}

function GoiY({ sp, them }: { sp: SanPham; them: (sp: SanPham, donViId: number, soLuong: number) => void }) {
  const [donVi, setDonVi] = useState(sp.don_vi[sp.don_vi.length - 1]?.id ?? sp.don_vi[0]?.id)
  const [sl, setSl] = useState(1)
  return (
    <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
      <span>
        {sp.ten} {sp.loai_san_pham === 'thuoc_ke_don' && <Tag color="red">Kê đơn</Tag>}
        <Typography.Text type="secondary"> · tồn {sp.ton_kha_dung} {sp.don_vi_co_so}{sp.hoat_chat.length ? ` · ${sp.hoat_chat.join(', ')}` : ''}</Typography.Text>
      </span>
      <Space>
        <Select value={donVi} onChange={setDonVi} style={{ width: 120 }} options={sp.don_vi.map((x) => ({ value: x.id, label: `${x.ten_don_vi} · ${dinhDangTien(x.gia_ban)}` }))} />
        <InputNumber min={1} max={9999} value={sl} onChange={(v) => setSl(v ?? 1)} />
        <Button size="small" onClick={() => donVi && them(sp, donVi, sl)}>Thêm</Button>
      </Space>
    </Space>
  )
}
