/** Logic thuần của tìm kiếm (KVL04): chuẩn hóa từ khóa và đường dẫn, cùng quy tắc với backend (`modules/cua_hang/tim_kiem.py`). */
import type { components } from '../../api/schema'

export type GoiY = components['schemas']['GoiYTimKiem']

export const TOI_THIEU_KY_TU = 2
export const TOI_DA_KY_TU = 100
export const TRE_GOI_Y_MS = 250

/** Gộp khoảng trắng, bỏ đầu cuối, cắt ở 100 ký tự. */
export function chuanHoaTuKhoa(q: string | null | undefined): string {
  return (q ?? '').replace(/\s+/g, ' ').trim().slice(0, TOI_DA_KY_TU).trim()
}

export function duDieuKienTim(q: string): boolean {
  return chuanHoaTuKhoa(q).length >= TOI_THIEU_KY_TU
}

export function duongDanTimKiem(q: string): string {
  return `/tim-kiem?q=${encodeURIComponent(chuanHoaTuKhoa(q))}`
}

/** Đích khi chọn một gợi ý: sản phẩm mở thẳng chi tiết, hoạt chất chạy tìm kiếm theo tên đó. */
export function duongDanGoiY(g: GoiY): string {
  return g.kieu === 'san_pham' && g.slug ? `/san-pham/${g.slug}?nguon=tim_kiem` : duongDanTimKiem(g.ten)
}
