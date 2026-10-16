/** Giới hạn ảnh tải lên ở giao diện (cùng giá trị với backend `core/luu_tru.py`; máy chủ vẫn kiểm tra lại theo nội dung thật). */

export const DUNG_LUONG_ANH_TOI_DA = 5 * 1024 * 1024
export const KIEU_ANH = ['image/jpeg', 'image/png', 'image/webp']

/** Lỗi của tệp chọn từ máy (chỉ để báo sớm), hoặc `null` nếu dùng được. */
export function loiTepAnh(tep: { type: string; size: number }): string | null {
  if (!KIEU_ANH.includes(tep.type)) return 'Chỉ nhận ảnh JPEG, PNG hoặc WebP'
  if (tep.size > DUNG_LUONG_ANH_TOI_DA) return 'Ảnh tối đa 5 MB'
  if (tep.size === 0) return 'Tệp rỗng'
  return null
}
