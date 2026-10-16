/**
 * Logic thuần của màn quản lý nội dung website (AD07): nhãn, kiểm tra ô nhập (cùng quy tắc với backend
 * `modules/noi_dung_web/schemas.py`), chuyển đổi dữ liệu form. Có test bảng ca (`noiDungWeb.test.ts`).
 */
import type { components } from '../../../api/schema'
import { chuoiHoacNull, gonTen, loiDuongDan, loiTen, loiVanBan } from '../../../lib/duLieuChung'

export type BannerRa = components['schemas']['BannerRa']
export type BaiVietAdmin = components['schemas']['BaiVietAdmin']
export type BaiVietTomTat = components['schemas']['BaiVietTomTatAdmin']
export type LoaiBai = BaiVietTomTat['loai']
export type TrangThaiBai = BaiVietTomTat['trang_thai']

export const KHOA_QUERY_NOI_DUNG = ['quan-tri', 'noi-dung'] as const
export const KICH_THUOC_BANG = 20

export const GIOI_HAN = { tieuDeBai: 255, noiDungBai: 100_000, tieuDeBanner: 200 } as const

export const LOAI_BAI: readonly { value: LoaiBai; label: string; so_nhieu: string }[] = [
  { value: 'bai_viet', label: 'Bài viết sức khỏe', so_nhieu: 'bài viết' },
  { value: 'chinh_sach', label: 'Chính sách', so_nhieu: 'chính sách' },
  { value: 'faq', label: 'Hỏi đáp thường gặp', so_nhieu: 'câu hỏi' },
]

export const VI_TRI_BANNER = [
  { value: 'trang_chu_chinh', label: 'Trang chủ: banner chính' },
  { value: 'trang_chu_phu', label: 'Trang chủ: banner phụ' },
] as const

const TINH_TRANG_BANNER: Record<BannerRa['tinh_trang'], { nhan: string; mau: string }> = {
  dang_hien: { nhan: 'Đang hiển thị', mau: 'success' },
  da_tat: { nhan: 'Đã tắt', mau: 'default' },
  chua_den_gio: { nhan: 'Chưa tới giờ', mau: 'processing' },
  het_han: { nhan: 'Đã hết hạn', mau: 'warning' },
}
export const nhanBanner = (t: BannerRa['tinh_trang']) => TINH_TRANG_BANNER[t]

/** Nhãn trạng thái của bài: bài sức khỏe `nhap` là CHỜ DƯỢC SĨ DUYỆT (không phải "bản nháp" của người soạn). */
export function nhanBai(loai: LoaiBai, trangThai: TrangThaiBai): { nhan: string; mau: string } {
  if (trangThai === 'da_duyet') return { nhan: 'Đang đăng', mau: 'success' }
  if (trangThai === 'luu_tru') return { nhan: 'Đã gỡ', mau: 'default' }
  return loai === 'bai_viet' ? { nhan: 'Chờ dược sĩ duyệt', mau: 'processing' } : { nhan: 'Bản nháp', mau: 'default' }
}

/** Sửa bài sức khỏe ĐANG ĐĂNG thì nó về chờ duyệt (và biến khỏi website): giao diện phải cảnh báo trước khi lưu. */
export function suaSeVeChoDuyet(loai: LoaiBai, trangThai: TrangThaiBai, daDoiNoiDung: boolean): boolean {
  return loai === 'bai_viet' && trangThai === 'da_duyet' && daDoiNoiDung
}

// --- Bài viết ----------------------------------------------------------------------------------------------------------

export interface GiaTriBai {
  tieu_de: string
  noi_dung: string
  anh_bia_url: string
  dua_vao_ai: boolean
}
export const BAI_TRONG: GiaTriBai = { tieu_de: '', noi_dung: '', anh_bia_url: '', dua_vao_ai: false }

export const giaTriTuBai = (b: BaiVietAdmin): GiaTriBai => ({
  tieu_de: b.tieu_de,
  noi_dung: b.noi_dung,
  anh_bia_url: b.anh_bia_url ?? '',
  dua_vao_ai: b.dua_vao_ai,
})

export type LoiBai = Partial<Record<keyof GiaTriBai, string>>

export function kiemTraBai(g: GiaTriBai): LoiBai {
  const loi: LoiBai = {}
  const ten = loiTen(g.tieu_de, GIOI_HAN.tieuDeBai)
  if (ten) loi.tieu_de = ten.replace('tên', 'tiêu đề')
  else if (!/[\p{L}\p{N}]/u.test(g.tieu_de)) loi.tieu_de = 'Tiêu đề phải có chữ hoặc số'
  if (g.noi_dung.trim() === '') loi.noi_dung = 'Vui lòng nhập nội dung'
  else {
    const l = loiVanBan(g.noi_dung, GIOI_HAN.noiDungBai, true)
    if (l) loi.noi_dung = l
  }
  const anh = loiDuongDan(g.anh_bia_url)
  if (anh) loi.anh_bia_url = anh
  return loi
}

/** Thân `POST /noi-bo/bai-viet`. */
export const baiRaTao = (loai: LoaiBai, g: GiaTriBai) => ({
  loai,
  tieu_de: gonTen(g.tieu_de),
  noi_dung: g.noi_dung.trim(),
  anh_bia_url: chuoiHoacNull(g.anh_bia_url),
  dua_vao_ai: g.dua_vao_ai,
})

/** Thân `PATCH`: chỉ trường đã đổi so với bản gốc lúc mở (không ghi đè phần người khác vừa sửa). */
export function baiRaSua(goc: BaiVietAdmin, g: GiaTriBai) {
  const ra: { tieu_de?: string; noi_dung?: string; anh_bia_url?: string | null; dua_vao_ai?: boolean } = {}
  if (gonTen(g.tieu_de) !== goc.tieu_de) ra.tieu_de = gonTen(g.tieu_de)
  if (g.noi_dung.trim() !== goc.noi_dung) ra.noi_dung = g.noi_dung.trim()
  if (chuoiHoacNull(g.anh_bia_url) !== goc.anh_bia_url) ra.anh_bia_url = chuoiHoacNull(g.anh_bia_url)
  if (g.dua_vao_ai !== goc.dua_vao_ai) ra.dua_vao_ai = g.dua_vao_ai
  return ra
}

/** Có đổi tiêu đề, nội dung hay ảnh bìa không (các trường làm bài đã duyệt phải duyệt lại). */
export const daDoiNoiDungBai = (ra: ReturnType<typeof baiRaSua>) => 'tieu_de' in ra || 'noi_dung' in ra || 'anh_bia_url' in ra

// --- Banner ------------------------------------------------------------------------------------------------------------

export interface GiaTriBanner {
  tieu_de: string
  anh_url: string
  lien_ket: string
  vi_tri: string
  thu_tu: number | null
  bat_dau: string | null // ISO có múi giờ
  ket_thuc: string | null
  dang_hien: boolean
}
export const BANNER_TRONG: GiaTriBanner = {
  tieu_de: '',
  anh_url: '',
  lien_ket: '',
  vi_tri: 'trang_chu_chinh',
  thu_tu: 0,
  bat_dau: null,
  ket_thuc: null,
  dang_hien: true,
}

export const giaTriTuBanner = (b: BannerRa): GiaTriBanner => ({
  tieu_de: b.tieu_de ?? '',
  anh_url: b.anh_url,
  lien_ket: b.lien_ket ?? '',
  vi_tri: b.vi_tri,
  thu_tu: b.thu_tu,
  bat_dau: b.bat_dau,
  ket_thuc: b.ket_thuc,
  dang_hien: b.dang_hien,
})

export type LoiBanner = Partial<Record<keyof GiaTriBanner, string>>

export function kiemTraBanner(g: GiaTriBanner): LoiBanner {
  const loi: LoiBanner = {}
  const tieuDe = loiVanBan(g.tieu_de, GIOI_HAN.tieuDeBanner)
  if (tieuDe) loi.tieu_de = tieuDe
  if (g.anh_url.trim() === '') loi.anh_url = 'Vui lòng chọn ảnh'
  else {
    const anh = loiDuongDan(g.anh_url)
    if (anh) loi.anh_url = anh
  }
  const lienKet = loiDuongDan(g.lien_ket)
  if (lienKet) loi.lien_ket = lienKet
  if (!VI_TRI_BANNER.some((v) => v.value === g.vi_tri)) loi.vi_tri = 'Vui lòng chọn vị trí'
  if (g.thu_tu === null || !Number.isInteger(g.thu_tu) || g.thu_tu < 0 || g.thu_tu > 9999) {
    loi.thu_tu = 'Thứ tự là số nguyên từ 0 đến 9999'
  }
  if (g.bat_dau && g.ket_thuc && new Date(g.ket_thuc).getTime() <= new Date(g.bat_dau).getTime()) {
    loi.ket_thuc = 'Thời điểm kết thúc phải sau thời điểm bắt đầu'
  }
  return loi
}

export const bannerRaTao = (g: GiaTriBanner) => ({
  tieu_de: chuoiHoacNull(g.tieu_de),
  anh_url: g.anh_url.trim(),
  lien_ket: chuoiHoacNull(g.lien_ket),
  vi_tri: g.vi_tri as 'trang_chu_chinh' | 'trang_chu_phu',
  thu_tu: g.thu_tu ?? 0,
  bat_dau: g.bat_dau,
  ket_thuc: g.ket_thuc,
  dang_hien: g.dang_hien,
})

/** Thân `PATCH` banner: chỉ trường đã đổi. */
export function bannerRaSua(goc: BannerRa, g: GiaTriBanner) {
  const day = bannerRaTao(g)
  const ra: Partial<ReturnType<typeof bannerRaTao>> = {}
  if (day.tieu_de !== goc.tieu_de) ra.tieu_de = day.tieu_de
  if (day.anh_url !== goc.anh_url) ra.anh_url = day.anh_url
  if (day.lien_ket !== goc.lien_ket) ra.lien_ket = day.lien_ket
  if (day.vi_tri !== goc.vi_tri) ra.vi_tri = day.vi_tri
  if (day.thu_tu !== goc.thu_tu) ra.thu_tu = day.thu_tu
  if (!cungThoiDiem(day.bat_dau, goc.bat_dau)) ra.bat_dau = day.bat_dau
  if (!cungThoiDiem(day.ket_thuc, goc.ket_thuc)) ra.ket_thuc = day.ket_thuc
  if (day.dang_hien !== goc.dang_hien) ra.dang_hien = day.dang_hien
  return ra
}

/** Hai chuỗi ISO có cùng thời điểm không (múi giờ biểu diễn khác nhau vẫn là một). */
export function cungThoiDiem(a: string | null, b: string | null): boolean {
  if (a === null || b === null) return a === b
  return new Date(a).getTime() === new Date(b).getTime()
}

/**
 * Sau khi máy chủ báo bản ghi đã bị người khác đổi (409): lấy giá trị MỚI của máy chủ, chỉ giữ lại những ô người dùng
 * ĐÃ SỬA so với bản họ mở (`goc`). Ô họ không đụng tới lấy theo bản mới, nên lưu tiếp không ghi đè phần người kia vừa sửa.
 */
export function gopThayDoi<T extends object>(dangGo: T, goc: T, moi: T): T {
  const ra = { ...moi }
  for (const k of Object.keys(dangGo) as (keyof T)[]) {
    if (JSON.stringify(dangGo[k]) !== JSON.stringify(goc[k])) ra[k] = dangGo[k]
  }
  return ra
}
