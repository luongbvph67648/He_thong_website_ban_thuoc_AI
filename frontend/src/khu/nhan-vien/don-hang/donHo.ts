import type { components } from '../../../api/schema'

export type DonHoVao = components['schemas']['DonHoVao']
export type KhachTim = components['schemas']['KhachTimRa']
export type DonQuay = components['schemas']['DonQuayRa']

export interface DongHo {
  san_pham_id: number
  don_vi_id: number
  ten: string
  ten_don_vi: string
  gia: string
  so_luong: number
}

/** Gộp các dòng cùng sản phẩm và đơn vị (cộng số lượng), giữ thứ tự thêm đầu tiên. */
export function themDong(ds: readonly DongHo[], moi: DongHo): DongHo[] {
  const co = ds.some((d) => d.san_pham_id === moi.san_pham_id && d.don_vi_id === moi.don_vi_id)
  if (!co) return [...ds, moi]
  return ds.map((d) => (d.san_pham_id === moi.san_pham_id && d.don_vi_id === moi.don_vi_id ? { ...d, so_luong: d.so_luong + moi.so_luong } : d))
}

/** Tạm tính theo giá hiện hành của đơn vị; số cuối cùng (giảm giá, phí ship) do máy chủ tính khi lập đơn. */
export function tamTinh(ds: readonly DongHo[]): number {
  return ds.reduce((tong, d) => tong + Math.round(Number(d.gia)) * d.so_luong, 0)
}
