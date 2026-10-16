/**
 * Dữ liệu và kiểm tra của form sản phẩm (AD04), cùng quy tắc với backend (`schemas_san_pham.py`; spec 06 mục 3.11).
 * Hàm thuần để test từng ca; trang chỉ nối chúng với Ant Design.
 */
import { chuoiHoacNull, gonTen, loiTen, loiVanBan } from './duLieuChung'

export const MA_VACH = /^[0-9A-Za-z._-]{1,50}$/
export const SKU = /^[A-Z0-9][A-Z0-9._-]{0,49}$/
export const TIEN_TOI_DA = 10 ** 12
export const HE_SO_TOI_DA = 1_000_000

/** Một dòng đơn vị trong form. `khoa` chỉ để React phân biệt dòng (đơn vị mới chưa có `id`). */
export interface DonViForm {
  khoa: string
  id?: number
  ten_don_vi: string
  he_so: number | null
  gia_ban: number | null
  ban_online: boolean
  la_mac_dinh: boolean
  ma_vach: string
}

export interface DonViApi {
  id: number
  ten_don_vi: string
  he_so: number
  gia_ban: string
  ban_online: boolean
  la_mac_dinh: boolean
  ma_vach: string | null
}

let boDem = 0
export const khoaMoi = () => `moi-${++boDem}`

export function donViTuApi(d: DonViApi): DonViForm {
  return {
    khoa: `id-${d.id}`,
    id: d.id,
    ten_don_vi: d.ten_don_vi,
    he_so: d.he_so,
    gia_ban: Number(d.gia_ban),
    ban_online: d.ban_online,
    la_mac_dinh: d.la_mac_dinh,
    ma_vach: d.ma_vach ?? '',
  }
}

export function donViMoi(truong: Partial<DonViForm> = {}): DonViForm {
  return { khoa: khoaMoi(), ten_don_vi: '', he_so: null, gia_ban: null, ban_online: true, la_mac_dinh: false, ma_vach: '', ...truong }
}

/** Khóa so sánh tên: không phân biệt hoa thường và dấu ("Hộp" và "hop" là một), như backend. */
export function khoaTen(ten: string): string {
  return gonTen(ten).replace(/đ/g, 'd').replace(/Đ/g, 'D').normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
}

export interface LoiDonVi {
  /** Lỗi của cả danh sách. */
  chung: string[]
  /** Lỗi theo chỉ số dòng rồi tên trường. */
  theoDong: Record<number, Partial<Record<'ten_don_vi' | 'he_so' | 'gia_ban' | 'ma_vach', string>>>
}

const laSoNguyen = (v: number | null): v is number => typeof v === 'number' && Number.isInteger(v)

/** Quy tắc của danh sách đơn vị (spec 06 mục 3.11). `coLoi` cho biết có thể lưu hay không. */
export function kiemTraDonVi(ds: readonly DonViForm[]): LoiDonVi & { coLoi: boolean } {
  const chung: string[] = []
  const theoDong: LoiDonVi['theoDong'] = {}
  const dat = (i: number, truong: keyof LoiDonVi['theoDong'][number], loi: string) => ((theoDong[i] ??= {})[truong] = loi)

  if (ds.length === 0) chung.push('Sản phẩm phải có ít nhất một đơn vị (đơn vị cơ sở)')
  ds.forEach((d, i) => {
    const loiTenDv = loiTen(d.ten_don_vi, 30)
    if (loiTenDv) dat(i, 'ten_don_vi', loiTenDv)
    if (!laSoNguyen(d.he_so) || d.he_so < 1 || d.he_so > HE_SO_TOI_DA) dat(i, 'he_so', `Số nguyên từ 1 đến ${HE_SO_TOI_DA.toLocaleString('vi-VN')}`)
    if (!laSoNguyen(d.gia_ban) || d.gia_ban < 0 || d.gia_ban >= TIEN_TOI_DA) dat(i, 'gia_ban', 'Số tiền đồng nguyên, không âm')
    if (d.ma_vach.trim() !== '' && !MA_VACH.test(d.ma_vach.trim())) dat(i, 'ma_vach', 'Chữ, số, dấu chấm, gạch dưới, gạch ngang; tối đa 50 ký tự')
  })
  if (ds.length > 0 && ds.filter((d) => d.he_so === 1).length !== 1) chung.push('Phải có đúng một đơn vị cơ sở (hệ số 1)')
  if (ds.filter((d) => d.la_mac_dinh).length > 1) chung.push('Chỉ được một đơn vị mặc định')
  const ten = ds.map((d) => khoaTen(d.ten_don_vi)).filter(Boolean)
  if (new Set(ten).size !== ten.length) chung.push('Tên đơn vị không được trùng nhau')
  const vach = ds.map((d) => d.ma_vach.trim().toUpperCase()).filter(Boolean)
  if (new Set(vach).size !== vach.length) chung.push('Mã vạch không được trùng giữa các đơn vị')
  return { chung, theoDong, coLoi: chung.length > 0 || Object.keys(theoDong).length > 0 }
}

/** Phần tử `don_vi` gửi lên API (ô trống thành `null`, tiền là chuỗi số nguyên, không float). */
export function donViRaApi(d: DonViForm) {
  return {
    ...(d.id !== undefined ? { id: d.id } : {}),
    ten_don_vi: gonTen(d.ten_don_vi),
    he_so: d.he_so as number,
    gia_ban: String(d.gia_ban),
    ban_online: d.ban_online,
    la_mac_dinh: d.la_mac_dinh,
    ma_vach: chuoiHoacNull(d.ma_vach),
  }
}

export interface ThanhPhanForm {
  khoa: string
  hoat_chat_id: number | null
  ten_hoat_chat: string
  ham_luong: string
}

export function thanhPhanMoi(): ThanhPhanForm {
  return { khoa: khoaMoi(), hoat_chat_id: null, ten_hoat_chat: '', ham_luong: '' }
}

export function kiemTraThanhPhan(ds: readonly ThanhPhanForm[]): { chung: string[]; theoDong: Record<number, string>; coLoi: boolean } {
  const chung: string[] = []
  const theoDong: Record<number, string> = {}
  ds.forEach((t, i) => {
    if (t.hoat_chat_id === null) theoDong[i] = 'Chọn một hoạt chất'
    else {
      const loi = loiVanBan(t.ham_luong, 50)
      if (loi) theoDong[i] = loi
    }
  })
  const ids = ds.map((t) => t.hoat_chat_id).filter((x): x is number => x !== null)
  if (new Set(ids).size !== ids.length) chung.push('Mỗi hoạt chất chỉ được xuất hiện một lần')
  return { chung, theoDong, coLoi: chung.length > 0 || Object.keys(theoDong).length > 0 }
}

export function loiSku(s: string): string | null {
  const sku = s.trim().toUpperCase()
  if (sku === '') return 'Vui lòng nhập SKU'
  return SKU.test(sku) ? null : 'SKU gồm chữ, số, dấu chấm, gạch dưới, gạch ngang; tối đa 50 ký tự'
}

/** Thông điệp khi vi phạm quy tắc giữa các trường (như `vi_pham_cheo` ở backend), hoặc `null`. */
export function loiCheo(f: { dung_dinh_ky: boolean; so_ngay: number | null; loai: string; la_noi_bat: boolean }): { truong: string; loi: string } | null {
  if (f.dung_dinh_ky && f.so_ngay === null) return { truong: 'so_ngay_dung_moi_don_vi', loi: 'Dùng định kỳ thì phải có số ngày dùng cho mỗi đơn vị' }
  if (!f.dung_dinh_ky && f.so_ngay !== null) return { truong: 'so_ngay_dung_moi_don_vi', loi: 'Chỉ sản phẩm dùng định kỳ mới có số ngày dùng cho mỗi đơn vị' }
  if (f.la_noi_bat && f.loai === 'thuoc_ke_don') return { truong: 'la_noi_bat', loi: 'Không đặt thuốc kê đơn làm sản phẩm nổi bật' }
  return null
}

const TRUONG_DON_VI = ['ten_don_vi', 'he_so', 'gia_ban', 'ma_vach'] as const

/**
 * Lỗi máy chủ (`loiTheoTruong`) về dạng của form đơn vị: `don_vi.2.ma_vach` là ô mã vạch của dòng thứ 3 (đếm từ 0), các
 * lỗi còn lại (cả danh sách, hay trường không có ô riêng) hiện chung để người dùng vẫn thấy.
 */
export function loiDonViTuApi(theoTruong: Record<string, string>): LoiDonVi {
  const chung: string[] = []
  const theoDong: LoiDonVi['theoDong'] = {}
  for (const [khoa, loi] of Object.entries(theoTruong)) {
    const m = /^don_vi\.(\d+)\.(\w+)$/.exec(khoa)
    const truong = TRUONG_DON_VI.find((t) => t === m?.[2])
    if (m && truong) (theoDong[Number(m[1])] ??= {})[truong] = loi
    else chung.push(loi)
  }
  return { chung, theoDong }
}

/** Như `loiDonViTuApi` cho thành phần: `thanh_phan.1.hoat_chat_id` / `.ham_luong` là lỗi của dòng thứ 2. */
export function loiThanhPhanTuApi(theoTruong: Record<string, string>): { chung: string[]; theoDong: Record<number, string> } {
  const chung: string[] = []
  const theoDong: Record<number, string> = {}
  for (const [khoa, loi] of Object.entries(theoTruong)) {
    const m = /^thanh_phan\.(\d+)\.(hoat_chat_id|ham_luong)$/.exec(khoa)
    if (m) theoDong[Number(m[1])] = loi
    else chung.push(loi)
  }
  return { chung, theoDong }
}
