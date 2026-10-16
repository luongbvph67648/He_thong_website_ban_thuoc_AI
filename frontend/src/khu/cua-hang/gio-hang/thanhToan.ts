import type { components } from '../../../api/schema'
import type { LoiApi } from '../../../api/loi'

export type DatHangVao = components['schemas']['DatHangVao']
export type DonHangRa = components['schemas']['DonHangRa']
export type XemTruocRa = components['schemas']['XemTruocRa']

export const NHAN_PHUONG_THUC: Record<'cod' | 'vnpay' | 'momo', string> = {
  cod: 'Thanh toán khi nhận hàng (COD)',
  vnpay: 'VNPay',
  momo: 'MoMo',
}

export interface FormDat {
  hinhThuc: 'giao_tan_noi' | 'nhan_tai_nha_thuoc'
  phuongThuc: 'cod' | 'vnpay' | 'momo'
  diaChiId: number | null
  maGiamGia: string | null
  ghiChu: string
}

/** Thân gửi lên: địa chỉ chỉ có khi giao tận nơi, mã/ghi chú rỗng thì bỏ. Khách không gửi dòng hàng (đơn dựng từ giỏ). */
export function thanDatHang(f: FormDat, tongKyVong?: string): DatHangVao {
  return {
    hinh_thuc_nhan: f.hinhThuc,
    phuong_thuc_tt: f.phuongThuc,
    ...(f.hinhThuc === 'giao_tan_noi' && f.diaChiId ? { dia_chi_id: f.diaChiId } : {}),
    ...(f.maGiamGia ? { ma_giam_gia: f.maGiamGia } : {}),
    ...(f.ghiChu.trim() ? { ghi_chu: f.ghiChu.trim() } : {}),
    ...(tongKyVong ? { tong_tien_ky_vong: tongKyVong } : {}),
  }
}

/** Đủ thông tin để tính thử: giao tận nơi thì phải chọn địa chỉ. */
export function duDieuKien(f: FormDat): boolean {
  return f.hinhThuc === 'nhan_tai_nha_thuoc' || f.diaChiId !== null
}

export interface KhoaDat {
  dau: string
  khoa: string
}

/**
 * Idempotency-Key cho lần bấm "Đặt hàng": giữ nguyên khóa khi nội dung không đổi (bấm lại sau lỗi mạng không tạo đơn
 * thứ hai), sinh khóa mới khi nội dung đổi hoặc lần trước đã có phản hồi dứt khoát từ máy chủ.
 */
export function khoaChoLanDat(truoc: KhoaDat | null, dau: string, taoMoi: () => string = () => crypto.randomUUID()): KhoaDat {
  return truoc && truoc.dau === dau ? truoc : { dau, khoa: taoMoi() }
}

/** Phản hồi dứt khoát (mã lỗi nghiệp vụ) thì lần sau phải dùng khóa mới; lỗi mạng (`loi = null`) thì giữ khóa. */
export function canKhoaMoi(loi: LoiApi | null): boolean {
  return loi !== null
}

export function giaThayDoi(loi: LoiApi | null): XemTruocRa | null {
  if (loi?.ma_loi !== 'GIA_DA_THAY_DOI') return null
  const ct = loi.chi_tiet as { tam_tinh: string; giam_gia: string; phi_van_chuyen: string; tong_tien: string }
  return { ...ct, ma_giam_gia: null }
}
