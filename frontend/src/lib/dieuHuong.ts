import { coMotTrong, type QuyenCuaToi } from './quyen'

/** Một trang của khu nội bộ: đường dẫn (tính từ gốc khu, `/` là trang chủ khu), nhãn, mã quyền và mã chức năng. */
export interface MucDieuHuong {
  duong: string
  nhan: string
  /** Có một trong các mã này (mức xem trở lên) là vào được trang. */
  quyen: readonly string[]
  chucNang: readonly string[]
  nhom?: string
  /** `false` cho trang con (chi tiết, tạo mới) không hiện ở menu. */
  trongMenu?: boolean
}

/** Admin vào khu quản trị; dược sĩ và nhân viên kho vào khu nhân viên (spec 09 mục 1). */
export function duongSauDangNhap(vaiTro?: string): '/quan-tri' | '/nhan-vien' {
  return vaiTro === 'ADMIN' ? '/quan-tri' : '/nhan-vien'
}

/** Mục menu đầu tiên mà người dùng có quyền, để `/nhan-vien` tự chuyển tới. `null` nếu chưa được cấp quyền nào. */
export function trangDauTienDuocPhep(muc: readonly MucDieuHuong[], quyen: QuyenCuaToi): string | null {
  return muc.find((m) => m.trongMenu !== false && coMotTrong(quyen, m.quyen, 'xem'))?.duong ?? null
}
