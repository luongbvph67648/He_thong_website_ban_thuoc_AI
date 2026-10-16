import { bangNhau } from './cauHinh'

/** Bảng chứa dữ liệu sức khỏe: nhật ký chỉ có tên bảng và id bản ghi, backend không bao giờ trả giá trị (spec 03 mục 5.1). */
export const BANG_SUC_KHOE: ReadonlySet<string> = new Set(['ho_so_suc_khoe', 'di_ung'])

const HANH_DONG: Record<string, string> = {
  tao: 'Tạo',
  sua: 'Sửa',
  xoa: 'Xóa',
  khoa: 'Khóa',
  mo_khoa: 'Mở khóa',
  duyet: 'Duyệt',
  dang_nhap: 'Đăng nhập',
  khoa_tam: 'Khóa tạm',
  doi_mat_khau: 'Đổi mật khẩu',
  dat_lai_mat_khau: 'Đặt lại mật khẩu',
  doc_suc_khoe: 'Đọc dữ liệu sức khỏe',
}

/** Mã hành động đã biết sang tiếng Việt; mã mới (module sau thêm) giữ nguyên để không giấu thông tin. */
export function nhanHanhDong(ma: string): string {
  return HANH_DONG[ma] ?? ma
}

export interface DongSoSanh {
  /** `null` khi giá trị không phải đối tượng (một giá trị duy nhất). */
  truong: string | null
  cu: unknown
  moi: unknown
  doi: boolean
}

const laDoiTuong = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)
const khongCo = (v: unknown) => (v === null ? undefined : v)

/** So giá trị cũ và mới của một dòng nhật ký, từng trường một nếu cả hai là đối tượng (hoặc một bên không có). */
export function soSanhGiaTri(cu: unknown, moi: unknown): DongSoSanh[] {
  if (cu == null && moi == null) return []
  const theoTruong = (laDoiTuong(cu) || cu == null) && (laDoiTuong(moi) || moi == null)
  if (!theoTruong) return [{ truong: null, cu: khongCo(cu), moi: khongCo(moi), doi: !bangNhau(cu, moi) }]
  const a = laDoiTuong(cu) ? cu : {}
  const b = laDoiTuong(moi) ? moi : {}
  return [...new Set([...Object.keys(a), ...Object.keys(b)])].sort().map((truong) => ({
    truong,
    cu: a[truong],
    moi: b[truong],
    doi: !(truong in a && truong in b && bangNhau(a[truong], b[truong])),
  }))
}
