import { api } from '../../../api/client'
import { goi } from '../../../api/goi'

/** Chuyển cả trang sang cổng thanh toán (tách ra để test thay thế được). */
export const chuyenSangCong = {
  di: (url: string) => window.location.assign(url),
}

/** Tạo giao dịch mới cho đơn đang chờ thanh toán rồi trả URL của cổng. Mỗi lần bấm là một khóa mới (thanh toán lại). */
export async function layUrlThanhToan(maDon: string) {
  return goi(() =>
    api.POST('/api/v1/toi/don-hang/{ma_don}/thanh-toan', {
      params: { path: { ma_don: maDon }, header: { 'Idempotency-Key': crypto.randomUUID() } },
    }),
  )
}

export const LA_ONLINE = (pt: string | null | undefined) => pt === 'vnpay' || pt === 'momo'

/** Mã đơn nằm trước dấu `-` cuối cùng của mã tham chiếu giao dịch (`<ma_don>-<id>`). */
export function maDonTuGiaoDich(giaoDich: string): string {
  const i = giaoDich.lastIndexOf('-')
  return i > 0 ? giaoDich.slice(0, i) : ''
}
