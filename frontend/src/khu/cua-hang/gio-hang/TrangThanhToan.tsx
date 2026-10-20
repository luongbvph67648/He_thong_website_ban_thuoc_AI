import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Descriptions, Empty, Input, Modal, QRCode, Radio, Select, Space, Spin, Typography } from 'antd'
import { useRef, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
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
import { LA_ONLINE, layUrlThanhToan } from './thanhToanOnline'

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
  const maTuGio = (useLocation().state as { maGiamGia?: string } | null)?.maGiamGia
  const qc = useQueryClient()
  const g = useGioHang()
  const [form, setForm] = useState<FormDat>({ hinhThuc: 'giao_tan_noi', phuongThuc: 'cod', diaChiId: null, maGiamGia: null, ghiChu: '' })
  const [giaMoi, datGiaMoi] = useState<XemTruocRa | null>(null)
  const [dangDat, datDangDat] = useState(false)
  const [thanhToanQr, datThanhToanQr] = useState<{
    maDon: string
    tongTien: string
    phuongThuc: 'vnpay' | 'momo'
    hanThanhToan: string | null
    url: string
  } | null>(null)
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
    // Ghi chú không ảnh hưởng giá: để ngoài khóa, gõ ghi chú không tính lại (tổng không nhảy, nút Đặt hàng không khóa)
    queryKey: ['don-hang', 'xem-truoc', thanDatHang({ ...dat, ghiChu: '' }), g.gio.tam_tinh],
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
      if (LA_ONLINE(r.data.phuong_thuc_tt)) {
        const tt = await layUrlThanhToan(r.data.ma_don)
        if (tt.ok) {
          datThanhToanQr({
            maDon: r.data.ma_don,
            tongTien: r.data.tong_tien,
            phuongThuc: r.data.phuong_thuc_tt as 'vnpay' | 'momo',
            hanThanhToan: tt.data.han_thanh_toan ?? r.data.han_thanh_toan,
            url: new URL(tt.data.url_thanh_toan, window.location.origin).toString(),
          })
          return
        }
        void message.warning('Đơn đã được tạo nhưng chưa mở được cổng thanh toán. Bạn có thể bấm "Thanh toán lại" ở trang sau.')
      }
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

  // Đặt hàng xong giỏ đã trống: vẫn phải giữ trang để hộp thoại QR còn hiện
  if (!g.dangTai && g.gio.dong.length === 0 && !thanhToanQr) {
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
        {LA_ONLINE(form.phuongThuc) && (
          <Alert
            type="info"
            showIcon
            style={{ marginTop: 12 }}
            message={`Sau khi bấm “Đặt hàng”, mã QR ${NHAN_PHUONG_THUC[form.phuongThuc]} sẽ hiện cùng mã đơn, số tiền và hạn thanh toán.`}
          />
        )}
      </Card>
      <Card title="Mã giảm giá và ghi chú" size="small">
        <Space orientation="vertical" style={{ width: '100%' }}>
          <OMaGiamGia khiDoi={khiDoiMa} maBanDau={maTuGio} />
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
      <Modal
        title="Quét mã để thanh toán"
        open={thanhToanQr !== null}
        width={540}
        className="thanh-toan-qr-modal"
        onCancel={() => {
          if (!thanhToanQr) return
          navigate(`/thanh-toan/ket-qua?ma=${encodeURIComponent(thanhToanQr.maDon)}`)
        }}
        footer={null}
        destroyOnHidden
      >
        {thanhToanQr && (
          <Space orientation="vertical" size="middle" className="thanh-toan-qr-noi-dung">
            <Typography.Text type="secondary" className="thanh-toan-qr-huong-dan">
              Dùng ứng dụng {NHAN_PHUONG_THUC[thanhToanQr.phuongThuc]} để quét mã và xác nhận giao dịch.
            </Typography.Text>
            <div className="thanh-toan-qr-khung">
              <QRCode type="svg" value={thanhToanQr.url} size={224} color="#1677ff" bordered={false} />
            </div>
            <div className="thanh-toan-qr-so-tien">
              <Typography.Text type="secondary">Số tiền cần thanh toán</Typography.Text>
              <Typography.Title level={2}>{dinhDangTien(thanhToanQr.tongTien)}</Typography.Title>
            </div>
            <Descriptions bordered size="small" column={1} className="thanh-toan-qr-thong-tin" items={[
              { key: 'ma', label: 'Mã đơn hàng', children: thanhToanQr.maDon },
              { key: 'pt', label: 'Phương thức', children: NHAN_PHUONG_THUC[thanhToanQr.phuongThuc] },
              ...(thanhToanQr.hanThanhToan ? [{ key: 'han', label: 'Thanh toán trước', children: dinhDangNgay(thanhToanQr.hanThanhToan, 'ngayGio') }] : []),
            ]} />
            <Button type="primary" size="large" block href={thanhToanQr.url} target="_blank" rel="noreferrer">
              Mở trang thanh toán
            </Button>
            <Button block onClick={() => navigate(`/thanh-toan/ket-qua?ma=${encodeURIComponent(thanhToanQr.maDon)}`)}>
              Kiểm tra trạng thái đơn hàng
            </Button>
            <Typography.Text type="secondary" className="thanh-toan-qr-luu-y">
              Chỉ xác nhận hoàn tất khi ứng dụng thanh toán báo giao dịch thành công.
            </Typography.Text>
          </Space>
        )}
      </Modal>
    </Space>
  )
}
