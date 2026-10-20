import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Result, Spin } from 'antd'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import GiaMomo from './cong-gia/GiaMomo'
import GiaVnpay from './cong-gia/GiaVnpay'
import type { GiaoDichGia, NguonMoPhong } from './cong-gia/hooks'

/** Giao dịch ở máy chủ mô phỏng VNPay/MoMo (`THANH_TOAN_CHE_DO=mo_phong`): đọc bằng chính tham số đã ký trên URL. */
async function docGiaoDichMoPhong(nguon: NguonMoPhong): Promise<GiaoDichGia | null> {
  const url =
    nguon.cong === 'vnpay'
      ? `/api/v1/mo-phong/vnpay/giao-dich?${nguon.query}`
      : `/api/v1/mo-phong/momo/giao-dich?token=${encodeURIComponent(nguon.token)}`
  const r = await fetch(url) // trang đối tác mô phỏng không đăng nhập, không đi qua client API của cửa hàng
  if (!r.ok) return null
  const d = (await r.json()) as { tham_chieu: string; ma_don: string; so_tien: number; cong: string; trang_thai: string; het_han_luc?: string | null }
  return { giao_dich: d.tham_chieu, ma_don: d.ma_don, so_tien: d.so_tien, cong: d.cong, trang_thai: d.trang_thai, het_han_luc: d.het_han_luc, nguon }
}

/**
 * Trang thanh toán của đối tác MÔ PHỎNG: dựng giao diện VNPay hoặc MoMo. Hai cách vào:
 * - `?cong=vnpay&vnp_...` / `?cong=momo&token=...` (`THANH_TOAN_CHE_DO=mo_phong`): URL do máy chủ mô phỏng cấp, kết quả
 *   gửi cho đối tác mô phỏng, nơi gửi IPN đúng định dạng thật rồi trả khách về `ReturnUrl` có chữ ký.
 * - `?giao_dich=...` (`THANH_TOAN_CHE_DO=gia`, cổng giả dùng cho test): IPN giả.
 * Không có tiền thật.
 */
export default function TrangCongGia() {
  const [tham] = useSearchParams()
  const cong = tham.get('cong')
  const giaoDich = tham.get('giao_dich') ?? ''
  let nguon: NguonMoPhong | null = null
  if (cong === 'vnpay') {
    const q = new URLSearchParams(tham)
    q.delete('cong')
    nguon = { cong: 'vnpay', query: q.toString() }
  } else if (cong === 'momo' && tham.get('token')) nguon = { cong: 'momo', token: tham.get('token') ?? '' }

  const q = useQuery({
    queryKey: ['cong-gia', cong, giaoDich, nguon],
    enabled: nguon !== null || giaoDich !== '',
    retry: false,
    staleTime: Infinity,
    queryFn: async () =>
      nguon
        ? docGiaoDichMoPhong(nguon)
        : ((await api.GET('/api/v1/webhook/gia-giao-dich', { params: { query: { giao_dich: giaoDich } } })).data ?? null),
  })
  if (!nguon && giaoDich === '') return <Alert type="error" showIcon message="Thiếu mã giao dịch" />
  if (q.isLoading) return <Spin />
  const gd = q.data
  if (!gd) return <Result status="404" title="Không tìm thấy giao dịch" extra={<Link to="/"><Button type="primary">Về trang chủ</Button></Link>} />
  if (gd.trang_thai !== 'khoi_tao') {
    return (
      <Result
        status="info"
        title="Giao dịch này đã được xử lý"
        extra={<Link to={`/thanh-toan/ket-qua?ma=${encodeURIComponent(gd.ma_don)}`}><Button type="primary">Xem đơn hàng</Button></Link>}
      />
    )
  }
  return gd.cong === 'momo' ? <GiaMomo gd={gd} /> : <GiaVnpay gd={gd} />
}
