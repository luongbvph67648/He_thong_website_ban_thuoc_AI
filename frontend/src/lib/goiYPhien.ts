import type { LoaiPhien } from '../stores/phien'

/**
 * Gợi ý "trước đó đã đăng nhập" để biết có nên thử làm mới phiên khi tải trang. Chỉ chứa loại phiên (`khach` hoặc
 * `noi_bo`): KHÔNG phải token hay hồ sơ, nên không vi phạm quy tắc không để bí mật trong localStorage (QĐ-08).
 * Không có gợi ý thì khách vãng lai không gọi API làm mới thừa (và không có lỗi 401 vô nghĩa trong console).
 */
const KHOA = 'phien_goi_y'

export function docGoiY(): LoaiPhien | null {
  try {
    const gia_tri = globalThis.localStorage?.getItem(KHOA)
    return gia_tri === 'khach' || gia_tri === 'noi_bo' ? gia_tri : null
  } catch {
    return null
  }
}

export function luuGoiY(loai: LoaiPhien): void {
  try {
    globalThis.localStorage?.setItem(KHOA, loai)
  } catch {
    // Trình duyệt chặn lưu trữ (chế độ riêng tư): chỉ mất khả năng tự đăng nhập lại khi tải trang.
  }
}

export function xoaGoiY(): void {
  try {
    globalThis.localStorage?.removeItem(KHOA)
  } catch {
    // như trên
  }
}
