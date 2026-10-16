/** Giới hạn ảnh sản phẩm ở giao diện (cùng giá trị với backend `core/luu_tru.py` và `san_pham_anh.py`; máy chủ vẫn kiểm tra lại). */

export const ANH_TOI_DA = 20
export const DUNG_LUONG_ANH_TOI_DA = 5 * 1024 * 1024
export const KIEU_ANH = ['image/jpeg', 'image/png', 'image/webp']

/** Lỗi của tệp chọn từ máy (chỉ để báo sớm; máy chủ vẫn kiểm tra lại theo nội dung thật). */
export function loiTepAnh(tep: { type: string; size: number }): string | null {
  if (!KIEU_ANH.includes(tep.type)) return 'Chỉ nhận ảnh JPEG, PNG hoặc WebP'
  if (tep.size > DUNG_LUONG_ANH_TOI_DA) return 'Ảnh tối đa 5 MB'
  if (tep.size === 0) return 'Tệp rỗng'
  return null
}
