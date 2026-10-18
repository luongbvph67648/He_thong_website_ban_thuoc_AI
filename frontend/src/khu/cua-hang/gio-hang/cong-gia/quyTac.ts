/**
 * Quy tắc của cổng thanh toán GIẢ (mô phỏng): số thẻ thử nghiệm, mã OTP, mã PIN. Chỉ có tác dụng ở môi trường mô phỏng
 * (`THANH_TOAN_CHE_DO=gia`); không có tiền thật. Số thẻ thử nghiệm theo bộ thẻ công khai trong tài liệu sandbox VNPay.
 */

export const OTP_THU_NGHIEM = '123456'
export const PIN_THU_NGHIEM = '123456'
export const SO_LAN_NHAP_TOI_DA = 3

export type KetQuaThe = 'hop_le' | 'khong_du_so_du' | 'chua_kich_hoat' | 'sai_thong_tin'

export const THE_THU_NGHIEM = [
  { soThe: '9704198526191432198', ten: 'NGUYEN VAN A', ngay: '07/15', mo_ta: 'Thanh toán thành công (OTP 123456)', ket_qua: 'hop_le' as const },
  { soThe: '9704195798459170488', ten: 'NGUYEN VAN A', ngay: '07/15', mo_ta: 'Thẻ không đủ số dư', ket_qua: 'khong_du_so_du' as const },
  { soThe: '9704192181368742', ten: 'NGUYEN VAN A', ngay: '07/15', mo_ta: 'Thẻ chưa kích hoạt thanh toán online', ket_qua: 'chua_kich_hoat' as const },
]

export const LY_DO_THAT_BAI: Record<Exclude<KetQuaThe, 'hop_le' | 'sai_thong_tin'>, string> = {
  khong_du_so_du: 'Thẻ không đủ số dư để thực hiện giao dịch.',
  chua_kich_hoat: 'Thẻ chưa đăng ký dịch vụ thanh toán trực tuyến.',
}

const chuanSo = (s: string) => s.replace(/\D/g, '')
const chuanTen = (s: string) =>
  s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/gi, 'd')
    .replace(/\s+/g, ' ')
    .trim()
    .toUpperCase()

/** Khớp cả ba thông tin (số thẻ, tên chủ thẻ không phân biệt dấu và hoa thường, ngày phát hành MM/YY) với bộ thẻ thử nghiệm. */
export function kiemTraThe(vao: { soThe: string; ten: string; ngay: string }): KetQuaThe {
  const the = THE_THU_NGHIEM.find((t) => t.soThe === chuanSo(vao.soThe))
  if (!the) return 'sai_thong_tin'
  if (chuanTen(vao.ten) !== the.ten) return 'sai_thong_tin'
  if (vao.ngay.trim() !== the.ngay) return 'sai_thong_tin'
  return the.ket_qua
}

/** Định dạng đồng hồ đếm ngược `mm:ss` (không âm). */
export function dongHoDemNguoc(giayCon: number): string {
  const g = Math.max(0, Math.floor(giayCon))
  return `${String(Math.floor(g / 60)).padStart(2, '0')}:${String(g % 60).padStart(2, '0')}`
}
