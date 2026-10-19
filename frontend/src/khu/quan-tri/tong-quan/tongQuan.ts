/** Phép tính thuần cho trang Tổng quan (AD14): kỳ báo cáo, so sánh kỳ trước, danh sách việc cần xử lý. */
import type { Dayjs } from 'dayjs'
import dayjs from '../../../lib/dayjs'

export type Khoang = [Dayjs, Dayjs]
export type MauKy = 'hom_nay' | '7_ngay' | '30_ngay' | 'thang_nay'

export const MAU_KY: readonly { value: MauKy; label: string }[] = [
  { value: 'hom_nay', label: 'Hôm nay' },
  { value: '7_ngay', label: '7 ngày' },
  { value: '30_ngay', label: '30 ngày' },
  { value: 'thang_nay', label: 'Tháng này' },
]

/** Khoảng ngày của một mẫu kỳ, kết thúc ở `homNay` (gồm cả hai đầu). */
export function khoangMau(mau: MauKy, homNay: Dayjs = dayjs()): Khoang {
  const cuoi = homNay.startOf('day')
  switch (mau) {
    case 'hom_nay':
      return [cuoi, cuoi]
    case '7_ngay':
      return [cuoi.subtract(6, 'day'), cuoi]
    case '30_ngay':
      return [cuoi.subtract(29, 'day'), cuoi]
    case 'thang_nay':
      return [cuoi.startOf('month'), cuoi]
  }
}

/** Mẫu kỳ trùng với khoảng đang chọn (để sáng nút), không trùng thì `undefined`. */
export function mauCuaKhoang(k: Khoang, homNay: Dayjs = dayjs()): MauKy | undefined {
  return MAU_KY.find(({ value }) => {
    const m = khoangMau(value, homNay)
    return m[0].isSame(k[0], 'day') && m[1].isSame(k[1], 'day')
  })?.value
}

export const soNgay = (k: Khoang) => k[1].startOf('day').diff(k[0].startOf('day'), 'day') + 1

/** Kỳ liền trước, cùng số ngày, kết thúc ngay trước ngày đầu kỳ đang xem. */
export function kyTruoc(k: Khoang): Khoang {
  const n = soNgay(k)
  const cuoi = k[0].startOf('day').subtract(1, 'day')
  return [cuoi.subtract(n - 1, 'day'), cuoi]
}

export const thamSoKy = (k: Khoang) => ({ tu_ngay: k[0].format('YYYY-MM-DD'), den_ngay: k[1].format('YYYY-MM-DD') })

/** Tỉ lệ thay đổi so với kỳ trước (0.25 = tăng 25%). Kỳ trước bằng 0 thì không so được: `null`. */
export function thayDoi(nay: string | number, truoc: string | number | undefined): number | null {
  if (truoc === undefined) return null
  const a = Number(nay)
  const b = Number(truoc)
  if (!Number.isFinite(a) || !Number.isFinite(b) || b === 0) return null
  return (a - b) / Math.abs(b)
}

/** Phần chia an toàn cho chỉ số hiển thị (biên lợi nhuận, giá trị trung bình): mẫu bằng 0 thì `null`. */
export function chia(tu: string | number, mau: string | number): number | null {
  const a = Number(tu)
  const b = Number(mau)
  return Number.isFinite(a) && Number.isFinite(b) && b !== 0 ? a / b : null
}

export const phanTram = (v: number | null | undefined, so = 1) => (v == null ? '—' : `${(v * 100).toFixed(so).replace('.', ',')}%`)

/** Cộng các số tiền dạng chuỗi (`"125000.50"`) bằng BigInt theo xu, không qua float. Trả chuỗi 2 chữ số lẻ. */
export function congTien(ds: readonly string[]): string {
  let xu = 0n
  for (const s of ds) {
    const k = /^(-?)(\d+)(?:\.(\d{1,2})\d*)?$/.exec(s.trim())
    if (!k) continue
    const v = BigInt(k[2]) * 100n + BigInt((k[3] ?? '').padEnd(2, '0'))
    xu += k[1] ? -v : v
  }
  const am = xu < 0n
  const tuyet = am ? -xu : xu
  return `${am ? '-' : ''}${tuyet / 100n}.${String(tuyet % 100n).padStart(2, '0')}`
}

/** Số tiền rút gọn cho trục biểu đồ: 1.250.000 -> `1,3 tr`, 25.000 -> `25 N`. */
export function tienNgan(v: number): string {
  if (v >= 1e9) return `${(v / 1e9).toFixed(1).replace('.', ',')} tỷ`
  if (v >= 1e6) return `${(v / 1e6).toFixed(1).replace('.', ',')} tr`
  if (v >= 1e3) return `${Math.round(v / 1e3)} N`
  return String(Math.round(v))
}

export type MucDo = 'gap' | 'chu_y'

export interface Viec {
  khoa: string
  tieuDe: string
  so: number
  moTa: string
  mucDo: MucDo
  /** Đường dẫn trong khu quản trị (không có tiền tố `/quan-tri`); không có thì việc thuộc vai trò khác. */
  duong?: string
  nut?: string
}

export interface DauVaoViec {
  phieuChoDuyet?: number
  hoanTien?: { so: number; tongTien: string; thieuTaiKhoan: number }
  thuHoi?: { so: number; khachChuaXuLy: number }
  loHetHan?: number
  tonThap?: number
  loCanHan?: number
  donGiaoThatBai?: number
  donChoXacNhan?: number
  aiGanCo?: number
}

/**
 * Việc Admin cần đọc và xử lý, việc gấp lên trước, rồi theo số lượng giảm dần. Nguồn chưa tải hoặc không có quyền
 * (`undefined`) thì bỏ hẳn, không hiện như "0 việc" để khỏi báo ổn sai.
 */
export function dsViec(v: DauVaoViec, dinhDangTien: (s: string) => string): Viec[] {
  const ds: Viec[] = []
  const them = (x: Viec | null) => x && ds.push(x)
  if (v.phieuChoDuyet !== undefined)
    them({ khoa: 'phieu', tieuDe: 'Phiếu kho chờ duyệt', so: v.phieuChoDuyet, mucDo: 'gap', moTa: 'Điều chỉnh tồn, phiếu hủy, xuất trả NCC đang chờ bạn duyệt', duong: '/duyet-phieu', nut: 'Duyệt phiếu' })
  if (v.hoanTien)
    them({
      khoa: 'hoan-tien',
      tieuDe: 'Hoàn tiền chờ xác nhận',
      so: v.hoanTien.so,
      mucDo: 'gap',
      moTa: v.hoanTien.so === 0 ? 'Không có khoản hoàn nào đang chờ' : `Tổng ${dinhDangTien(v.hoanTien.tongTien)}${v.hoanTien.thieuTaiKhoan ? ` · ${v.hoanTien.thieuTaiKhoan} khoản khách chưa gửi tài khoản` : ''}`,
      duong: '/hoan-tien',
      nut: 'Xác nhận hoàn',
    })
  if (v.thuHoi)
    them({ khoa: 'thu-hoi', tieuDe: 'Lệnh thu hồi đang mở', so: v.thuHoi.so, mucDo: 'gap', moTa: v.thuHoi.khachChuaXuLy ? `Còn ${v.thuHoi.khachChuaXuLy} khách chưa được liên hệ` : 'Theo dõi tiến độ và đóng lệnh khi xong', duong: '/thu-hoi', nut: 'Theo dõi' })
  if (v.loHetHan !== undefined)
    them({ khoa: 'het-han', tieuDe: 'Lô hết hạn còn trong kho', so: v.loHetHan, mucDo: 'gap', moTa: 'Nhân viên kho cần lập phiếu hủy, bạn duyệt phiếu', duong: '/duyet-phieu', nut: 'Mở duyệt phiếu' })
  if (v.donGiaoThatBai !== undefined)
    them({ khoa: 'giao-that-bai', tieuDe: 'Đơn giao thất bại', so: v.donGiaoThatBai, mucDo: 'chu_y', moTa: 'Cần liên hệ khách giao lại hoặc nhận hoàn về kho', duong: '/xem/don-hang?trang_thai=giao_that_bai', nut: 'Xem đơn' })
  if (v.tonThap !== undefined)
    them({ khoa: 'ton-thap', tieuDe: 'Sản phẩm dưới tồn tối thiểu', so: v.tonThap, mucDo: 'chu_y', moTa: 'Nên lên kế hoạch nhập thêm hàng', duong: undefined })
  if (v.loCanHan !== undefined)
    them({ khoa: 'can-han', tieuDe: 'Lô cận hạn', so: v.loCanHan, mucDo: 'chu_y', moTa: 'Cân nhắc khuyến mãi để bán trước khi hết hạn', duong: '/khuyen-mai', nut: 'Tạo khuyến mãi' })
  if (v.donChoXacNhan !== undefined)
    them({ khoa: 'cho-xac-nhan', tieuDe: 'Đơn chờ dược sĩ xác nhận', so: v.donChoXacNhan, mucDo: 'chu_y', moTa: 'Đơn khách đặt chưa được xác nhận', duong: '/xem/don-hang?trang_thai=cho_xac_nhan', nut: 'Xem đơn' })
  if (v.aiGanCo !== undefined)
    them({ khoa: 'ai', tieuDe: 'Câu trả lời AI bị gắn cờ', so: v.aiGanCo, mucDo: 'chu_y', moTa: 'Trong kỳ đang xem; kiểm tra để chỉnh tri thức hoặc cấu hình AI', duong: '/giam-sat-ai', nut: 'Kiểm tra' })
  const hang = (x: Viec) => (x.so === 0 ? 2 : x.mucDo === 'gap' ? 0 : 1)
  return ds.sort((a, b) => hang(a) - hang(b) || b.so - a.so)
}
