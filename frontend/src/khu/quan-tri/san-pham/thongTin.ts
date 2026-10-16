/**
 * Dữ liệu và kiểm tra của tab "Thông tin" (AD04): đổi qua lại giữa giá trị form và body API, so sánh để chỉ gửi trường
 * đã đổi, và kiểm tra từng ô cùng quy tắc với backend (`schemas_san_pham.py`). Hàm thuần để test từng ca.
 */
import { chuoiHoacNull, gonTen, loiTen, loiVanBan } from '../../../lib/duLieuChung'
import { loiCheo, loiSku } from '../../../lib/sanPham'
import type { LuaChon } from './ChonDuLieuChung'
import type { LoaiSanPham, SanPhamChiTiet, TrangThaiKinhDoanh } from './sanPham'

/** Giá trị form. Thương hiệu và nhà sản xuất giữ cả tên để ô chọn hiện được mà không phải tải lại. */
export interface GiaTriThongTin {
  sku: string
  ten: string
  loai_san_pham: LoaiSanPham | undefined
  danh_muc_id: number | undefined
  thuong_hieu: LuaChon | null
  nha_san_xuat: LuaChon | null
  so_dang_ky: string
  dang_bao_che: string
  quy_cach: string
  doi_tuong_su_dung: string
  ton_toi_thieu: number | null
  dung_dinh_ky: boolean
  so_ngay_dung_moi_don_vi: number | null
  so_luong_toi_da_moi_don: number | null
  la_noi_bat: boolean
  trang_thai: TrangThaiKinhDoanh
}

export const THONG_TIN_MAC_DINH: GiaTriThongTin = {
  sku: '',
  ten: '',
  loai_san_pham: undefined,
  danh_muc_id: undefined,
  thuong_hieu: null,
  nha_san_xuat: null,
  so_dang_ky: '',
  dang_bao_che: '',
  quy_cach: '',
  doi_tuong_su_dung: '',
  ton_toi_thieu: 0,
  dung_dinh_ky: false,
  so_ngay_dung_moi_don_vi: null,
  so_luong_toi_da_moi_don: null,
  la_noi_bat: false,
  trang_thai: 'dang_kinh_doanh',
}

export const GIOI_HAN = { soDangKy: 50, dangBaoChe: 100, quyCach: 150, doiTuong: 150, ten: 255, soLuong: 1_000_000_000 } as const

export function thongTinTuApi(b: SanPhamChiTiet): GiaTriThongTin {
  return {
    sku: b.sku,
    ten: b.ten,
    loai_san_pham: b.loai_san_pham,
    danh_muc_id: b.danh_muc_id,
    thuong_hieu: b.thuong_hieu_id === null ? null : { value: b.thuong_hieu_id, label: b.ten_thuong_hieu ?? `#${b.thuong_hieu_id}` },
    nha_san_xuat: b.nha_san_xuat_id === null ? null : { value: b.nha_san_xuat_id, label: b.ten_nha_san_xuat ?? `#${b.nha_san_xuat_id}` },
    so_dang_ky: b.so_dang_ky ?? '',
    dang_bao_che: b.dang_bao_che ?? '',
    quy_cach: b.quy_cach ?? '',
    doi_tuong_su_dung: b.doi_tuong_su_dung ?? '',
    ton_toi_thieu: b.ton_toi_thieu,
    dung_dinh_ky: b.dung_dinh_ky,
    so_ngay_dung_moi_don_vi: b.so_ngay_dung_moi_don_vi === null ? null : Number(b.so_ngay_dung_moi_don_vi),
    so_luong_toi_da_moi_don: b.so_luong_toi_da_moi_don,
    la_noi_bat: b.la_noi_bat,
    trang_thai: b.trang_thai,
  }
}

/** Các trường thương mại dạng API (ô trống thành `null`; số ngày là chuỗi để không qua `float` khi gửi). */
export function thongTinRaApi(g: GiaTriThongTin) {
  return {
    sku: g.sku.trim().toUpperCase(),
    ten: gonTen(g.ten),
    loai_san_pham: g.loai_san_pham as LoaiSanPham,
    danh_muc_id: g.danh_muc_id as number,
    thuong_hieu_id: g.thuong_hieu?.value ?? null,
    nha_san_xuat_id: g.nha_san_xuat?.value ?? null,
    so_dang_ky: chuoiHoacNull(g.so_dang_ky),
    dang_bao_che: chuoiHoacNull(g.dang_bao_che),
    quy_cach: chuoiHoacNull(g.quy_cach),
    doi_tuong_su_dung: chuoiHoacNull(g.doi_tuong_su_dung),
    ton_toi_thieu: g.ton_toi_thieu as number,
    dung_dinh_ky: g.dung_dinh_ky,
    so_ngay_dung_moi_don_vi: g.so_ngay_dung_moi_don_vi === null ? null : String(g.so_ngay_dung_moi_don_vi),
    so_luong_toi_da_moi_don: g.so_luong_toi_da_moi_don,
    la_noi_bat: g.la_noi_bat,
    trang_thai: g.trang_thai,
  }
}

/**
 * Body PATCH: chỉ những trường khác bản gốc (`goc`, giá trị lúc mở form). Không gửi cả bản sửa nên người khác vừa đổi
 * một trường khác thì lần lưu này không ghi đè nó.
 */
export function thongTinRaSua(g: GiaTriThongTin, goc: GiaTriThongTin): Partial<ReturnType<typeof thongTinRaApi>> {
  const moi = thongTinRaApi(g)
  const cu = thongTinRaApi(goc)
  const khac = (Object.keys(moi) as (keyof typeof moi)[]).filter((k) => moi[k] !== cu[k])
  return Object.fromEntries(khac.map((k) => [k, moi[k]]))
}

/** Tên ô của form ứng với tên trường API khi hai bên khác nhau (ô chọn giữ cả tên nên không đặt theo `*_id`). */
export const O_THEO_TRUONG_API: Record<string, keyof GiaTriThongTin> = {
  thuong_hieu_id: 'thuong_hieu',
  nha_san_xuat_id: 'nha_san_xuat',
}

const CO_CHU_HOAC_SO = /[\p{L}\p{N}]/u
const laSoNguyen = (v: number | null) => typeof v === 'number' && Number.isInteger(v)

/** Lỗi theo tên ô của form (rỗng nếu hợp lệ). Giữ cùng quy tắc, cùng thứ tự với backend. */
export function kiemTraThongTin(g: GiaTriThongTin): Partial<Record<keyof GiaTriThongTin, string>> {
  const loi: Partial<Record<keyof GiaTriThongTin, string>> = {}
  const sku = loiSku(g.sku)
  if (sku) loi.sku = sku
  const ten = loiTen(g.ten, GIOI_HAN.ten)
  if (ten) loi.ten = ten
  else if (!CO_CHU_HOAC_SO.test(g.ten)) loi.ten = 'Tên phải có ít nhất một chữ hoặc số'
  if (!g.loai_san_pham) loi.loai_san_pham = 'Vui lòng chọn loại sản phẩm'
  if (g.danh_muc_id === undefined) loi.danh_muc_id = 'Vui lòng chọn danh mục'
  for (const [o, giaTri, toiDa] of [
    ['so_dang_ky', g.so_dang_ky, GIOI_HAN.soDangKy],
    ['dang_bao_che', g.dang_bao_che, GIOI_HAN.dangBaoChe],
    ['quy_cach', g.quy_cach, GIOI_HAN.quyCach],
    ['doi_tuong_su_dung', g.doi_tuong_su_dung, GIOI_HAN.doiTuong],
  ] as const) {
    const l = loiVanBan(giaTri, toiDa)
    if (l) loi[o] = l
  }
  if (!laSoNguyen(g.ton_toi_thieu) || (g.ton_toi_thieu as number) < 0 || (g.ton_toi_thieu as number) > GIOI_HAN.soLuong) {
    loi.ton_toi_thieu = `Số nguyên từ 0 đến ${GIOI_HAN.soLuong.toLocaleString('vi-VN')}`
  }
  const ngay = g.so_ngay_dung_moi_don_vi
  if (ngay !== null && (!(ngay > 0) || ngay >= 10_000 || Math.round(ngay * 100) / 100 !== ngay)) {
    loi.so_ngay_dung_moi_don_vi = 'Số dương nhỏ hơn 10.000, tối đa 2 chữ số lẻ'
  }
  const toiDa = g.so_luong_toi_da_moi_don
  if (toiDa !== null && (!laSoNguyen(toiDa) || toiDa < 1 || toiDa > GIOI_HAN.soLuong)) {
    loi.so_luong_toi_da_moi_don = `Số nguyên từ 1 đến ${GIOI_HAN.soLuong.toLocaleString('vi-VN')}, để trống là không giới hạn`
  }
  // Quy tắc giữa các trường chỉ hiện khi từng ô đã hợp lệ, để thông điệp không đè lên lỗi cụ thể hơn.
  if (!loi.so_ngay_dung_moi_don_vi && g.loai_san_pham) {
    const cheo = loiCheo({ dung_dinh_ky: g.dung_dinh_ky, so_ngay: ngay, loai: g.loai_san_pham, la_noi_bat: g.la_noi_bat })
    if (cheo) loi[cheo.truong as keyof GiaTriThongTin] = cheo.loi
  }
  return loi
}

const TEN_O = Object.keys(THONG_TIN_MAC_DINH) as (keyof GiaTriThongTin)[]

/** Tên trường API của một ô (ngược lại với `O_THEO_TRUONG_API`). */
export const truongApiCuaO = (o: keyof GiaTriThongTin): string => Object.entries(O_THEO_TRUONG_API).find(([, ten]) => ten === o)?.[0] ?? o

/**
 * Lỗi máy chủ (`loiTheoTruong`) về dạng của form thông tin: lỗi của ô nào vào ô đó; lỗi của đơn vị, thành phần hoặc
 * trường không có ô (ví dụ `phien_ban`) trả ở `khac` để trang hiện chung chứ không để mất.
 */
export function loiThongTinTuApi(theoTruong: Record<string, string>): { theoO: Partial<Record<keyof GiaTriThongTin, string>>; khac: string[] } {
  const theoO: Partial<Record<keyof GiaTriThongTin, string>> = {}
  const khac: string[] = []
  for (const [truong, loi] of Object.entries(theoTruong)) {
    const o = O_THEO_TRUONG_API[truong] ?? TEN_O.find((t) => t === truong)
    if (o) theoO[o] = loi
    else if (!/^(don_vi|thanh_phan)(\.|$)/.test(truong)) khac.push(loi)
  }
  return { theoO, khac }
}
