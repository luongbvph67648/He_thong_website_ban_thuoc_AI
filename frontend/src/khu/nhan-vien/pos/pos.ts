import type { components } from '../../../api/schema'

export type SanPhamPos = components['schemas']['SanPhamPos']

export interface DongPos {
  san_pham_id: number
  don_vi_id: number
  so_luong: number
  ten: string
  ten_don_vi: string
  gia: string
  ke_don: boolean
}

/** Thêm một dòng vào giỏ POS; cùng sản phẩm và đơn vị thì cộng dồn số lượng. */
export function themDongPos(ds: DongPos[], moi: DongPos): DongPos[] {
  const i = ds.findIndex((d) => d.san_pham_id === moi.san_pham_id && d.don_vi_id === moi.don_vi_id)
  if (i < 0) return [...ds, moi]
  return ds.map((d, k) => (k === i ? { ...d, so_luong: d.so_luong + moi.so_luong } : d))
}

export function tongPos(ds: DongPos[]): number {
  return ds.reduce((t, d) => t + Math.round(Number(d.gia)) * d.so_luong, 0)
}

/** Dòng giỏ từ kết quả tìm kiếm; `donViId` mặc định là đơn vị khớp mã vạch, rồi đơn vị nhỏ nhất (bán lẻ). */
export function dongTuSanPham(sp: SanPhamPos, donViId?: number, soLuong = 1): DongPos | null {
  const dv = sp.don_vi.find((d) => d.id === (donViId ?? sp.don_vi_khop_ma_vach)) ?? sp.don_vi[0]
  if (!dv) return null
  return {
    san_pham_id: sp.id,
    don_vi_id: dv.id,
    so_luong: soLuong,
    ten: sp.ten,
    ten_don_vi: dv.ten_don_vi,
    gia: dv.gia_ban,
    ke_don: sp.loai_san_pham === 'thuoc_ke_don',
  }
}
