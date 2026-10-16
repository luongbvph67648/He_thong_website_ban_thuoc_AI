import type { components } from '../api/schema'

export type TrangThaiDoiTra = components['schemas']['TrangThaiDoiTra']
export type LyDoDoiTra = components['schemas']['LyDoDoiTra']
export type HuongXuLy = components['schemas']['HuongXuLyDoiTra']

export const NHAN_TRANG_THAI_DOI_TRA: Record<TrangThaiDoiTra, { nhan: string; mau: string }> = {
  cho_duyet: { nhan: 'Chờ duyệt', mau: 'gold' },
  da_duyet: { nhan: 'Đã duyệt, chờ nhận hàng trả', mau: 'blue' },
  tu_choi: { nhan: 'Từ chối', mau: 'red' },
  kho_da_nhan: { nhan: 'Kho đã nhận hàng', mau: 'cyan' },
  hoan_tat: { nhan: 'Hoàn tất', mau: 'green' },
}

export const NHAN_LY_DO_DOI_TRA: Record<LyDoDoiTra, string> = {
  giao_sai_san_pham: 'Giao sai sản phẩm',
  sai_so_luong: 'Sai số lượng',
  hu_hong: 'Hàng hư hỏng',
  het_han_can_han: 'Hết hạn hoặc cận hạn',
  khac: 'Lý do khác (lỗi của nhà thuốc)',
}

export const NHAN_HUONG_XU_LY: Record<HuongXuLy, string> = {
  hoan_tien: 'Hoàn tiền',
  gui_hang_thay_the: 'Gửi hàng thay thế',
}

export const TEP_BANG_CHUNG = ['image/jpeg', 'image/png', 'image/webp', 'video/mp4']
export const TOI_DA_ANH_BYTE = 5 * 1024 * 1024
export const TOI_DA_VIDEO_BYTE = 30 * 1024 * 1024

/** Lỗi khi chọn tệp bằng chứng (kiểu và dung lượng); `null` nếu hợp lệ. */
export function loiTepBangChung(f: { name: string; type: string; size: number }): string | null {
  if (!TEP_BANG_CHUNG.includes(f.type)) return `${f.name}: chỉ nhận ảnh JPEG, PNG, WebP hoặc video MP4`
  if (f.type === 'video/mp4' ? f.size > TOI_DA_VIDEO_BYTE : f.size > TOI_DA_ANH_BYTE) return `${f.name}: quá dung lượng (ảnh 5 MB, video 30 MB)`
  return null
}
