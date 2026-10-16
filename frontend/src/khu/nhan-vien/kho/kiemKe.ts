import type { components } from '../../../api/schema'

type Dong = components['schemas']['DongKiemKe']

/** Chênh lệch = thực tế - sổ sách; `null` khi chưa nhập. */
export function chenhLech(soSach: number, thucTe: number | null | undefined): number | null {
  return thucTe === null || thucTe === undefined ? null : thucTe - soSach
}

/** Lọc dòng theo từ khóa (tên, SKU, số lô; không phân biệt hoa thường) và chỉ dòng lệch (tính cả số đang gõ chưa lưu). */
export function locDong(dong: Dong[], tuKhoa: string, chiLech: boolean, dangNhap: Record<number, number | null> = {}): Dong[] {
  const k = tuKhoa.trim().toLowerCase()
  return dong.filter((d) => {
    if (k && !`${d.san_pham.ten} ${d.san_pham.sku} ${d.so_lo}`.toLowerCase().includes(k)) return false
    if (!chiLech) return true
    const c = chenhLech(d.so_luong_so_sach, dangNhap[d.lo_id] ?? d.so_luong_thuc_te)
    return c !== null && c !== 0
  })
}
