import { PlusOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, DatePicker, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'
import dayjs from '../../../lib/dayjs'
import { lienKetAnToan } from '../../../lib/lienKet'
import { NutTaiAnh } from './NutTaiAnh'
import {
  BANNER_TRONG,
  KHOA_QUERY_NOI_DUNG,
  VI_TRI_BANNER,
  bannerRaSua,
  bannerRaTao,
  giaTriTuBanner,
  gopThayDoi,
  kiemTraBanner,
  nhanBanner,
  type BannerRa,
  type GiaTriBanner,
} from './noiDungWeb'

const KHOA = [...KHOA_QUERY_NOI_DUNG, 'banner']

type Mo = { kieu: 'tao' } | { kieu: 'sua'; goc: BannerRa } | null

/** Quản lý banner trang chủ (AD07): danh sách, thêm, sửa, xóa. Ghi cần quyền đầy đủ (chỉ Admin). */
export function TabBanner({ coGhi }: { coGhi: boolean }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [mo, setMo] = useState<Mo>(null)
  const [thongDiep, setThongDiep] = useState<string | null>(null)

  const ds = useQuery({
    queryKey: KHOA,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/banner')
      if (error) throw error
      return data
    },
  })

  const xoa = async (b: BannerRa) => {
    const kq = await goi(() =>
      api.DELETE('/api/v1/noi-bo/banner/{banner_id}', { params: { path: { banner_id: b.id }, query: { phien_ban: b.phien_ban } } }),
    )
    if (!kq.ok) {
      setThongDiep(kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI' ? 'Banner đã được người khác thay đổi, danh sách đã được tải lại. Hãy kiểm tra rồi xóa lại.' : thongDiepChung(kq.loi))
      void ds.refetch()
      return
    }
    setThongDiep(null)
    void message.success('Đã xóa banner')
    void queryClient.invalidateQueries({ queryKey: KHOA })
  }

  const cot: ColumnsType<BannerRa> = [
    {
      title: 'Ảnh',
      key: 'anh',
      width: 110,
      render: (_, b) => {
        const anh = lienKetAnToan(b.anh_url)
        return anh ? <img src={anh} alt={b.tieu_de ?? 'Banner'} style={{ width: 96, height: 40, objectFit: 'cover' }} /> : null
      },
    },
    { title: 'Tiêu đề', key: 'tieu_de', render: (_, b) => b.tieu_de ?? <Typography.Text type="secondary">(không có)</Typography.Text> },
    { title: 'Vị trí', key: 'vi_tri', render: (_, b) => VI_TRI_BANNER.find((v) => v.value === b.vi_tri)?.label ?? b.vi_tri },
    { title: 'Thứ tự', dataIndex: 'thu_tu', key: 'thu_tu', width: 80 },
    {
      title: 'Thời gian hiển thị',
      key: 'thoi_gian',
      render: (_, b) =>
        b.bat_dau || b.ket_thuc ? `${b.bat_dau ? dinhDangNgay(b.bat_dau, 'ngayGio') : '…'} đến ${b.ket_thuc ? dinhDangNgay(b.ket_thuc, 'ngayGio') : '…'}` : 'Luôn hiển thị',
    },
    { title: 'Tình trạng', key: 'tinh_trang', render: (_, b) => <Tag color={nhanBanner(b.tinh_trang).mau}>{nhanBanner(b.tinh_trang).nhan}</Tag> },
    {
      title: 'Thao tác',
      key: 'thao_tac',
      render: (_, b) =>
        coGhi && (
          <Space>
            <Button size="small" onClick={() => setMo({ kieu: 'sua', goc: b })}>
              Sửa
            </Button>
            <Popconfirm title="Xóa banner này?" description="Banner bị xóa hẳn, không khôi phục được." okText="Xóa" cancelText="Hủy" okButtonProps={{ danger: true }} onConfirm={() => xoa(b)}>
              <Button size="small" danger>
                Xóa
              </Button>
            </Popconfirm>
          </Space>
        ),
    },
  ]

  return (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      {thongDiep && <Alert type="error" showIcon title={thongDiep} closable={{ onClose: () => setThongDiep(null) }} />}
      <Space style={{ justifyContent: 'space-between', width: '100%' }} wrap>
        <Typography.Text type="secondary">Banner hiện ở trang chủ cửa hàng theo vị trí, thứ tự và khoảng thời gian.</Typography.Text>
        <YeuCauQuyen ma="cms.manage" kieu="nut">
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setMo({ kieu: 'tao' })}>
            Thêm banner
          </Button>
        </YeuCauQuyen>
      </Space>
      {ds.isError ? (
        <Alert type="error" showIcon title="Không tải được danh sách banner" action={<Button onClick={() => void ds.refetch()}>Thử lại</Button>} />
      ) : (
        <Table rowKey="id" size="middle" loading={ds.isPending} dataSource={ds.data ?? []} columns={cot} pagination={false} locale={{ emptyText: 'Chưa có banner' }} />
      )}
      {mo && (
        <FormBanner
          key={mo.kieu === 'sua' ? `sua-${mo.goc.id}` : 'tao'}
          mo={mo}
          onDong={() => setMo(null)}
          onXong={() => {
            setMo(null)
            void queryClient.invalidateQueries({ queryKey: KHOA })
          }}
        />
      )}
    </Space>
  )
}

function FormBanner({ mo, onDong, onXong }: { mo: NonNullable<Mo>; onDong: () => void; onXong: () => void }) {
  const { message } = App.useApp()
  const [goc, setGoc] = useState<BannerRa | null>(mo.kieu === 'sua' ? mo.goc : null)
  const [gia, setGia] = useState<GiaTriBanner>(goc ? giaTriTuBanner(goc) : BANNER_TRONG)
  const [loi, setLoi] = useState<Partial<Record<keyof GiaTriBanner, string>>>({})
  const [thongDiep, setThongDiep] = useState<string | null>(null)
  const [dangLuu, setDangLuu] = useState(false)
  const dat = (thayDoi: Partial<GiaTriBanner>) => setGia((g) => ({ ...g, ...thayDoi }))

  const luu = async () => {
    const sai = kiemTraBanner(gia)
    setLoi(sai)
    if (Object.keys(sai).length) return
    setDangLuu(true)
    const kq = goc
      ? await goi(() => api.PATCH('/api/v1/noi-bo/banner/{banner_id}', { params: { path: { banner_id: goc.id } }, body: { phien_ban: goc.phien_ban, ...bannerRaSua(goc, gia) } }))
      : await goi(() => api.POST('/api/v1/noi-bo/banner', { body: bannerRaTao(gia) }))
    setDangLuu(false)
    if (kq.ok) {
      void message.success(goc ? 'Đã lưu banner' : 'Đã thêm banner')
      return onXong()
    }
    if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI' && goc) {
      // Lấy bản mới của máy chủ, giữ ô mình đã sửa: lưu tiếp không ghi đè phần người kia vừa đổi.
      const moi = await goi(() => api.GET('/api/v1/noi-bo/banner'))
      const ban = moi.ok ? moi.data.find((b) => b.id === goc.id) : undefined
      if (ban) {
        setGia((g) => gopThayDoi(g, giaTriTuBanner(goc), giaTriTuBanner(ban)))
        setGoc(ban)
        return setThongDiep('Banner đã được người khác thay đổi. Form đã cập nhật theo bản mới và giữ phần bạn vừa sửa; kiểm tra rồi lưu lại.')
      }
      return setThongDiep('Banner đã bị xóa hoặc thay đổi, hãy đóng form và tải lại danh sách.')
    }
    if (kq.loi) {
      const theoTruong = loiTheoTruong(kq.loi)
      if (Object.keys(theoTruong).length) setLoi(theoTruong)
    }
    setThongDiep(thongDiepChung(kq.loi))
  }

  return (
    <Modal open title={goc ? 'Sửa banner' : 'Thêm banner'} okText="Lưu" cancelText="Hủy" confirmLoading={dangLuu} onOk={() => void luu()} onCancel={onDong} mask={{ closable: false }} destroyOnHidden width={560}>
      <Form layout="vertical" component="div">
        {thongDiep && <Alert type="warning" showIcon title={thongDiep} style={{ marginBottom: 16 }} />}
        <Form.Item label="Ảnh" required validateStatus={loi.anh_url ? 'error' : undefined} help={loi.anh_url}>
          <NutTaiAnh khu="banner" value={gia.anh_url} onChange={(anh_url) => dat({ anh_url })} />
        </Form.Item>
        <Form.Item label="Tiêu đề (dùng làm mô tả ảnh)" htmlFor="bn-tieu-de" validateStatus={loi.tieu_de ? 'error' : undefined} help={loi.tieu_de}>
          <Input id="bn-tieu-de" value={gia.tieu_de} maxLength={400} onChange={(e) => dat({ tieu_de: e.target.value })} />
        </Form.Item>
        <Form.Item label="Liên kết khi bấm vào (bắt đầu bằng / hoặc https://)" htmlFor="bn-lien-ket" validateStatus={loi.lien_ket ? 'error' : undefined} help={loi.lien_ket}>
          <Input id="bn-lien-ket" value={gia.lien_ket} placeholder="/danh-muc/thuc-pham-chuc-nang" onChange={(e) => dat({ lien_ket: e.target.value })} />
        </Form.Item>
        <Space align="start" size={16} wrap>
          <Form.Item label="Vị trí" required validateStatus={loi.vi_tri ? 'error' : undefined} help={loi.vi_tri}>
            <Select aria-label="Vị trí" style={{ width: 220 }} value={gia.vi_tri} options={[...VI_TRI_BANNER]} onChange={(vi_tri) => dat({ vi_tri })} />
          </Form.Item>
          <Form.Item label="Thứ tự" required validateStatus={loi.thu_tu ? 'error' : undefined} help={loi.thu_tu}>
            {/* Không đặt min/max: antd âm thầm ép giá trị về khoảng; khoảng được kiểm tra bằng kiemTraBanner. */}
            <InputNumber aria-label="Thứ tự" value={gia.thu_tu} precision={0} changeOnWheel={false} onChange={(thu_tu) => dat({ thu_tu })} />
          </Form.Item>
        </Space>
        <Space align="start" size={16} wrap>
          <Form.Item label="Bắt đầu hiển thị" validateStatus={loi.bat_dau ? 'error' : undefined} help={loi.bat_dau}>
            <DatePicker showTime aria-label="Bắt đầu hiển thị" format="DD/MM/YYYY HH:mm" value={gia.bat_dau ? dayjs(gia.bat_dau) : null} onChange={(d) => dat({ bat_dau: d ? d.toISOString() : null })} />
          </Form.Item>
          <Form.Item label="Kết thúc hiển thị" validateStatus={loi.ket_thuc ? 'error' : undefined} help={loi.ket_thuc}>
            <DatePicker showTime aria-label="Kết thúc hiển thị" format="DD/MM/YYYY HH:mm" value={gia.ket_thuc ? dayjs(gia.ket_thuc) : null} onChange={(d) => dat({ ket_thuc: d ? d.toISOString() : null })} />
          </Form.Item>
        </Space>
        <Form.Item label="Đang bật" htmlFor="bn-dang-hien">
          <Switch id="bn-dang-hien" checked={gia.dang_hien} onChange={(dang_hien) => dat({ dang_hien })} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
