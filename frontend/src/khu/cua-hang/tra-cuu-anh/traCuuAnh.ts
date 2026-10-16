export const KIEU_ANH_TRA_CUU = ['image/jpeg', 'image/png', 'image/webp']
export const TOI_DA_ANH_TRA_CUU_BYTE = 5 * 1024 * 1024

/** Lỗi chọn ảnh phía client (backend kiểm lại): chỉ jpeg/png/webp, tối đa 5 MB. */
export function loiAnhTraCuu(f: { type: string; size: number }): string | null {
  if (!KIEU_ANH_TRA_CUU.includes(f.type)) return 'Chỉ nhận ảnh JPEG, PNG hoặc WebP'
  if (f.size > TOI_DA_ANH_TRA_CUU_BYTE) return 'Ảnh tối đa 5 MB'
  if (f.size === 0) return 'Ảnh trống'
  return null
}
