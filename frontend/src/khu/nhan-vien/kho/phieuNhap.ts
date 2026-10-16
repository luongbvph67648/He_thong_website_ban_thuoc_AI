import type { components } from '../../../api/schema'

export type SanPham = components['schemas']['SanPhamTraCuu']

export interface DongForm {
  khoa: number
  sp: SanPham
  donViId: number
  soLo: string
  nsx: string
  hsd: string
  soLuong: number | null
  giaNhap: number | null
}

/** Tổng tiền phiếu theo số liệu đang nhập (số nguyên đồng, như backend). */
export function tongTienPhieu(dong: Pick<DongForm, 'soLuong' | 'giaNhap'>[]): number {
  return dong.reduce((t, d) => t + (d.soLuong ?? 0) * (d.giaNhap ?? 0), 0)
}

/** Chọn đơn vị của sản phẩm: ưu tiên đơn vị có đúng mã vạch vừa quét, rồi đơn vị mặc định. */
export function chonDonVi(sp: SanPham, maVach: string): number {
  return sp.don_vi.find((d) => d.ma_vach === maVach)?.id ?? sp.don_vi_mac_dinh_id ?? sp.don_vi[0].id
}
