import type { components } from '../../../api/schema'

export type DongSoan = components['schemas']['DongSoanRa']

/** Số lần đã quét theo `ct_don_hang_id`. */
export type DaQuet = Record<number, number>

/** Dòng đã đủ: quét đủ số lượng; sản phẩm không có mã vạch thì kho tự xác nhận bằng tay (tính là đủ khi đã bấm). */
export function dongXong(dong: Pick<DongSoan, 'ct_don_hang_id' | 'so_luong'>, daQuet: DaQuet): boolean {
  return (daQuet[dong.ct_don_hang_id] ?? 0) >= dong.so_luong
}

export function tatCaXong(dong: readonly DongSoan[], daQuet: DaQuet): boolean {
  return dong.length > 0 && dong.every((d) => dongXong(d, daQuet))
}

/**
 * Xử lý một mã vừa quét: tìm dòng chưa đủ có `ma_vach` khớp rồi tăng đếm. `null` nghĩa là mã không thuộc đơn (hoặc
 * dòng đó đã đủ), nơi gọi báo lỗi để kho không đóng nhầm hàng.
 */
export function quetMa(dong: readonly DongSoan[], daQuet: DaQuet, ma: string): DaQuet | null {
  const maSach = ma.trim()
  if (!maSach) return null
  const d = dong.find((x) => x.ma_vach === maSach && !dongXong(x, daQuet))
  return d ? { ...daQuet, [d.ct_don_hang_id]: (daQuet[d.ct_don_hang_id] ?? 0) + 1 } : null
}

/** Xác nhận tay cho dòng không có mã vạch: coi như đã đủ số lượng. */
export function xacNhanTay(dong: DongSoan, daQuet: DaQuet): DaQuet {
  return { ...daQuet, [dong.ct_don_hang_id]: dong.so_luong }
}

/** Sự kiện của màn "Giả lập vận chuyển" (chế độ giả): nhãn nút và trạng thái gửi như webhook của đối tác. */
export const SU_KIEN_GIA: readonly { trangThai: string; nhan: string }[] = [
  { trangThai: 'picked', nhan: 'Đã lấy hàng' },
  { trangThai: 'delivered', nhan: 'Giao thành công' },
  { trangThai: 'delivery_fail', nhan: 'Giao thất bại' },
  { trangThai: 'delivering', nhan: 'Giao lại' },
  { trangThai: 'returned', nhan: 'Đã hoàn hàng' },
]
