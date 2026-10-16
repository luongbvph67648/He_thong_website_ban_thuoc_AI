import type { components } from '../../../api/schema'

export type KhuyenMaiTomTat = components['schemas']['KhuyenMaiTomTat']
export type KhuyenMaiChiTiet = components['schemas']['KhuyenMaiChiTiet']
export type KhuyenMaiVao = components['schemas']['KhuyenMaiVao']
export type TrangThaiHieuLuc = KhuyenMaiTomTat['trang_thai']

export const KHOA_KHUYEN_MAI = ['quan-tri', 'khuyen-mai'] as const

export const NHAN_TRANG_THAI: Record<TrangThaiHieuLuc, { nhan: string; mau: string }> = {
  dang_hieu_luc: { nhan: 'Đang diễn ra', mau: 'green' },
  sap_dien_ra: { nhan: 'Sắp diễn ra', mau: 'blue' },
  het_han: { nhan: 'Hết hạn', mau: 'default' },
  da_tat: { nhan: 'Đã tắt', mau: 'red' },
}

/** "10 %" hoặc "50.000 ₫" (+ trần giảm). */
export function moTaMucGiam(km: Pick<KhuyenMaiTomTat, 'loai_giam' | 'gia_tri' | 'giam_toi_da'>, tien: (v: string) => string): string {
  if (km.loai_giam === 'so_tien') return tien(km.gia_tri)
  const phanTram = Number(km.gia_tri).toLocaleString('vi-VN', { maximumFractionDigits: 2 })
  return km.giam_toi_da ? `${phanTram}% (tối đa ${tien(km.giam_toi_da)})` : `${phanTram}%`
}

export interface GiaTriForm {
  ten: string
  loai_giam: 'phan_tram' | 'so_tien'
  gia_tri: number
  giam_toi_da?: number | null
  don_toi_thieu?: number | null
  thoi_gian: readonly [{ toISOString(): string }, { toISOString(): string }]
  tong_luot?: number | null
  luot_moi_khach: number
  pham_vi: 'toan_bo' | 'danh_muc' | 'san_pham'
  danh_muc_ids?: number[]
  san_pham_ids?: number[]
  dang_hoat_dong: boolean
}

/** Nội dung gửi API từ form: chỉ gửi phạm vi đúng loại, trần giảm chỉ với giảm theo phần trăm. */
export function guiTuForm(v: GiaTriForm): KhuyenMaiVao {
  return {
    ten: v.ten,
    loai_giam: v.loai_giam,
    gia_tri: String(v.gia_tri),
    giam_toi_da: v.loai_giam === 'phan_tram' && v.giam_toi_da ? String(v.giam_toi_da) : null,
    don_toi_thieu: String(v.don_toi_thieu ?? 0),
    bat_dau: v.thoi_gian[0].toISOString(),
    ket_thuc: v.thoi_gian[1].toISOString(),
    tong_luot: v.tong_luot ?? null,
    luot_moi_khach: v.luot_moi_khach,
    pham_vi: v.pham_vi,
    danh_muc_ids: v.pham_vi === 'danh_muc' ? (v.danh_muc_ids ?? []) : [],
    san_pham_ids: v.pham_vi === 'san_pham' ? (v.san_pham_ids ?? []) : [],
    dang_hoat_dong: v.dang_hoat_dong,
  }
}
