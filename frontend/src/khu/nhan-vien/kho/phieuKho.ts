import type { components } from '../../../api/schema'

export type TrangThaiDuyet = components['schemas']['TrangThaiDuyet']
export type KhuTon = components['schemas']['KhuTon']
export type LyDoHuy = components['schemas']['LyDoHuyHang']

export const NHAN_DUYET: Record<TrangThaiDuyet, { nhan: string; mau: string }> = {
  cho_duyet: { nhan: 'Chờ duyệt', mau: 'gold' },
  da_duyet: { nhan: 'Đã duyệt', mau: 'green' },
  tu_choi: { nhan: 'Từ chối', mau: 'red' },
}

export const NHAN_KHU: Record<KhuTon, string> = { kho_ban: 'Khu bán', biet_tru: 'Khu biệt trữ' }

export const NHAN_LY_DO_HUY: Record<LyDoHuy, string> = {
  het_han: 'Hết hạn',
  hu_hong: 'Hư hỏng',
  hang_tra_ve: 'Hàng trả về',
  thu_hoi: 'Thu hồi',
  khac: 'Khác',
}

export type LoaiPhieu = 'dieu-chinh' | 'huy' | 'xuat-tra'
export const NHAN_LOAI: Record<LoaiPhieu, string> = {
  'dieu-chinh': 'Điều chỉnh tồn',
  huy: 'Hủy hàng',
  'xuat-tra': 'Xuất trả NCC',
}

/** Số lượng tối đa chọn được ở khu đã chọn; khu bán không tính hàng đang giữ cho đơn (khớp backend). */
export function tonKhu(lo: { so_luong_ton: number | null; so_luong_giu: number | null; so_luong_biet_tru: number | null }, khu: KhuTon): number {
  if (khu === 'kho_ban') return (lo.so_luong_ton ?? 0) - (lo.so_luong_giu ?? 0)
  return lo.so_luong_biet_tru ?? 0
}

export interface DongNhap {
  lo_id: number | null
  tu_khu: KhuTon
  so_luong: number | null
}

/** Lỗi của form phiếu (chuỗi rỗng = hợp lệ): có dòng, mỗi dòng đã chọn lô và số lượng nguyên dương, không trùng (lô, khu). */
export function kiemTraDong(dong: DongNhap[]): string {
  if (!dong.length) return 'Cần ít nhất một dòng'
  const da = new Set<string>()
  for (const [i, d] of dong.entries()) {
    if (d.lo_id === null) return `Dòng ${i + 1}: chưa chọn lô`
    if (!Number.isInteger(d.so_luong) || (d.so_luong as number) < 1) return `Dòng ${i + 1}: số lượng phải là số nguyên từ 1`
    const khoa = `${d.lo_id}:${d.tu_khu}`
    if (da.has(khoa)) return `Dòng ${i + 1}: trùng lô và khu với dòng trước`
    da.add(khoa)
  }
  return ''
}
