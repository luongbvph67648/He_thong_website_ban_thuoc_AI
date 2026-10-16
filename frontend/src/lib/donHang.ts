import type { components } from '../api/schema'

export type TrangThaiDon = components['schemas']['TrangThaiDon']

/** Khách tự hủy được khi đơn chưa sang "Đang soạn hàng" (spec 04 dòng 9, 12, 14; backend kiểm tra lại). */
const KHACH_HUY_DUOC: readonly TrangThaiDon[] = ['cho_khach_xac_nhan', 'cho_thanh_toan', 'cho_xac_nhan', 'da_xac_nhan']
/** Dược sĩ hủy được khi hàng chưa rời kho (dòng 15, 19). */
const DUOC_SI_HUY_DUOC: readonly TrangThaiDon[] = ['cho_xac_nhan', 'da_xac_nhan', 'dang_soan_hang', 'cho_lay_hang']

export const khachHuyDuoc = (tt: TrangThaiDon): boolean => KHACH_HUY_DUOC.includes(tt)
export const duocSiXacNhanDuoc = (tt: TrangThaiDon): boolean => tt === 'cho_xac_nhan'
export const duocSiHuyDuoc = (tt: TrangThaiDon): boolean => DUOC_SI_HUY_DUOC.includes(tt)

export const NHAN_PHUONG_THUC_DON: Record<string, string> = {
  cod: 'COD',
  vnpay: 'VNPay',
  momo: 'MoMo',
  tien_mat: 'Tiền mặt',
  chuyen_khoan: 'Chuyển khoản',
}
