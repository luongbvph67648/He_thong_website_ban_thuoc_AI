/** Hằng và hàm dùng chung của các trang AD02 (không phải component nên tách khỏi file `.tsx`). */

/** Mọi truy vấn của AD02 nằm dưới khóa này: làm mới một lần là cả danh sách, chi tiết và lịch sử mua cùng cập nhật. */
export const KHOA_QUERY_KHACH = ['noi-bo', 'khach-hang'] as const

export interface TrangThaiTaiKhoanKhach {
  trang_thai: string
  khoa_den: string | null
}

/** Khóa tạm do đoán sai mật khẩu: còn hiệu lực khi `khoa_den` ở tương lai (tài khoản vẫn `hoat_dong`). */
export function dangKhoaTam(khach: TrangThaiTaiKhoanKhach, bayGio = new Date()): boolean {
  return khach.khoa_den !== null && new Date(khach.khoa_den) > bayGio
}

/** Admin đã khóa hoặc đang khóa tạm: cả hai đều mở khóa được bằng `mo-khoa`. */
export function dangBiKhoa(khach: TrangThaiTaiKhoanKhach): boolean {
  return khach.trang_thai === 'bi_khoa' || dangKhoaTam(khach)
}
