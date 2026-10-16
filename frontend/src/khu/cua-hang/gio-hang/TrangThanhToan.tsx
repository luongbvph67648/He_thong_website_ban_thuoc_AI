import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Descriptions, Empty, Input, Radio, Select, Space, Spin, Typography } from 'antd'
import { useRef, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { dinhDangTien } from '../../../lib/dinhDang'
import { usePhien } from '../../../stores/phien'
import { KHOA_GIO_HANG, useGioHang } from './gioHang'
import { OMaGiamGia, type KetQuaMa } from './OMaGiamGia'
import {
  canKhoaMoi,
  duDieuKien,
  type FormDat,
  giaThayDoi,
  khoaChoLanDat,
  type KhoaDat,
  NHAN_PHUONG_THUC,
  thanDatHang,
  type XemTruocRa,
} from './thanhToan'

/** KTV02, KTV03, KTV04: địa chỉ, hình thức nhận, phương thức thanh toán, mã giảm giá, tổng tiền rồi đặt hàng. */
export default function TrangThanhToan() {
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const khach = usePhien((s) => s.loai === 'khach')
  if (!daKhoiPhuc) return <Spin />
  if (!khach) return <Navigate to="/dang-nhap?tiep=/thanh-toan" replace />
  return <NoiDung />
}

function NoiDung() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const g = useGioHang()
  const [form, setForm] = useState<FormDat>({ hinhThuc: 'giao_tan_noi', phuongThuc: 'cod', diaChiId: null, maGiamGia: null, ghiChu: '' })
  const [giaMoi, datGiaMoi] = useState<XemTruocRa | null>(null)
  const [dangDat, datDangDat] = useState(false)
  const khoaRef = useRef<KhoaDat | null>(null)

  const diaChi = useQuery({
    queryKey: ['dia-chi'],
    queryFn: async () => (await api.GET('/api/v1/toi/dia-chi')).data ?? [],
  })
  const diaChiId = form.diaChiId ?? diaChi.data?.find((d) => d.la_mac_dinh)?.id ?? diaChi.data?.[0]?.id ?? null
  const dat: FormDat = { ...form, diaChiId }
  const than = thanDatHang(dat)
  const sanSang = duDieuKien(dat) && g.gio.dong.length > 0 && g.gio.dong.every((d) => d.mua_duoc)

  const xemTruoc = useQuery({
    queryKey: ['don-hang', 'xem-truoc', than, g.gio.tam_tinh],
    enabled: sanSang,
    queryFn: () => goi(() => api.POST('/api/v1/toi/don-hang/xem-truoc', { body: than })),
  })
  const kq = xemTruoc.data
  const tong: XemTruocRa | null = giaMoi ?? (kq?.ok ? kq.data : null)
  const loiTinh = kq && !kq.ok ? thongDiepChung(kq.loi) : null

  const doi = (p: Partial<FormDat>) => {
    datGiaMoi(null)
    setForm((f) => ({ ...f, ...p }))
  }
  const khiDoiMa = (m: KetQuaMa | null) => doi({ maGiamGia: m ? m.ma : null })

  async function datHang() {
    if (!tong) return
    datDangDat(true)
    const body = thanDatHang(dat, tong.tong_tien)
    khoaRef.current = khoaChoLanDat(khoaRef.current, JSON.stringify(body))
    const r = await goi(() =>
      api.POST('/api/v1/toi/don-hang', { body, params: { header: { 'Idempotency-Key': khoaRef.current!.khoa } } }),
    )
    datDangDat(false)
    if (r.ok) {
      khoaRef.current = null
      await qc.invalidateQueries({ queryKey: KHOA_GIO_HANG })
      navigate(`/thanh-toan/ket-qua?ma=${encodeURIComponent(r.data.ma_don)}`)
      return
    }
    if (canKhoaMoi(r.loi)) khoaRef.current = null
    const moi = giaThayDoi(r.loi)
    if (moi) {
      datGiaMoi(moi)
      void message.warning('Giá hoặc phí đã thay đổi, vui lòng xem lại tổng tiền rồi đặt hàng lần nữa.')
      return
    }
    void message.error(thongDiepChung(r.loi))
    await qc.invalidateQueries({ queryKey: KHOA_GIO_HANG })
  }

  if (!g.dangTai && g.gio.dong.length === 0) {
    return <Empty description="Giỏ hàng trống"><Link to="/">Tiếp tục mua sắm</Link></Empty>
  }
  return (
    <Space orientation="vertical" size="large" style={{ width: '100%', maxWidth: 720 }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Thanh toán</Typography.Title>
      {g.gio.dong.some((d) => !d.mua_duoc) && (
        <Alert type="warning" showIcon message="Có sản phẩm không còn mua được. Hãy quay lại giỏ hàng và xóa chúng." action={<Link to="/gio-hang">Về giỏ hàng</Link>} />
      )}
      <Card title="Hình thức nhận hàng" size="small">
        <Radio.Group value={form.hinhThuc} onChange={(e) => doi({ hinhThuc: e.target.value })}>
          <Radio value="giao_tan_noi">Giao tận nơi</Radio>
          <Radio value="nhan_tai_nha_thuoc">Nhận tại nhà thuốc</Radio>
        </Radio.Group>
        {form.hinhThuc === 'giao_tan_noi' && (
          <div style={{ marginTop: 12 }}>
            {diaChi.data && diaChi.data.length === 0 ? (
              <Alert type="info" showIcon message="Bạn chưa có địa chỉ giao hàng" action={<Link to="/tai-khoan">Thêm địa chỉ</Link>} />
            ) : (
              <Select
                aria-label="Địa chỉ giao hàng"
                style={{ width: '100%' }}
                loading={diaChi.isLoading}
                value={diaChiId ?? undefined}
                onChange={(v) => doi({ diaChiId: v })}
                options={(diaChi.data ?? []).map((d) => ({
                  value: d.id,
                  label: `${d.ten_nguoi_nhan} · ${d.so_dien_thoai} · ${[d.dia_chi_chi_tiet, d.ten_phuong_xa, d.ten_tinh].filter(Boolean).join(', ')}`,
                }))}
              />
            )}
          </div>
        )}
      </Card>
      <Card title="Phương thức thanh toán" size="small">
        <Radio.Group value={form.phuongThuc} onChange={(e) => doi({ phuongThuc: e.target.value })}>
          <Space orientation="vertical">
            {(Object.keys(NHAN_PHUONG_THUC) as (keyof typeof NHAN_PHUONG_THUC)[]).map((k) => (
              <Radio key={k} value={k}>{NHAN_PHUONG_THUC[k]}</Radio>
            ))}
          </Space>
        </Radio.Group>
      </Card>
      <Card title="Mã giảm giá và ghi chú" size="small">
        <Space orientation="vertical" style={{ width: '100%' }}>
          <OMaGiamGia khiDoi={khiDoiMa} />
          <Input.TextArea aria-label="Ghi chú cho đơn hàng" placeholder="Ghi chú cho đơn hàng (không bắt buộc)" maxLength={500} rows={2} value={form.ghiChu} onChange={(e) => doi({ ghiChu: e.target.value })} />
        </Space>
      </Card>
      <Card title="Tổng tiền" size="small">
        {loiTinh && <Alert type="error" showIcon message={loiTinh} style={{ marginBottom: 12 }} />}
        <Descriptions
          column={1}
          size="small"
          items={[
            { key: 'tt', label: 'Tạm tính', children: dinhDangTien(tong?.tam_tinh ?? g.gio.tam_tinh) },
            { key: 'gg', label: 'Giảm giá', children: tong ? `− ${dinhDangTien(tong.giam_gia)}` : '—' },
            { key: 'ship', label: 'Phí vận chuyển', children: tong ? dinhDangTien(tong.phi_van_chuyen) : '—' },
            { key: 'tong', label: <b>Tổng cộng</b>, children: <b>{tong ? dinhDangTien(tong.tong_tien) : '—'}</b> },
          ]}
        />
      </Card>
      <Button type="primary" size="large" loading={dangDat} disabled={!tong || !sanSang || !!loiTinh} onClick={() => void datHang()}>
        Đặt hàng
      </Button>
    </Space>
  )
}
