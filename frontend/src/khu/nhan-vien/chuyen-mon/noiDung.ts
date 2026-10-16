/** Dữ liệu và hàm thuần của màn nội dung chuyên môn (DS10): đổi qua lại form/API, kiểm tra ô nhập, so sánh phiên bản. */
import type { components } from '../../../api/schema'
import { chuoiHoacNull, loiDuongDan, loiVanBan } from '../../../lib/duLieuChung'

export type PhienBanNoiDung = components['schemas']['PhienBanNoiDung']
export type NoiDungSanPham = components['schemas']['NoiDungSanPham']
export type DongNoiDung = components['schemas']['DongNoiDung']
export type NoiDungVao = components['schemas']['NoiDungVao']

/** Mọi truy vấn của DS10 nằm dưới khóa này: làm mới một lần là cả danh sách lẫn chi tiết cùng cập nhật. */
export const KHOA_QUERY_CHUYEN_MON = ['noi-bo', 'chuyen-mon'] as const

export const TOI_DA_KY_TU = 20_000

export const TRUONG_VAN_BAN = [
  { ten: 'chi_dinh', nhan: 'Chỉ định' },
  { ten: 'chong_chi_dinh', nhan: 'Chống chỉ định' },
  { ten: 'lieu_dung_tham_khao', nhan: 'Liều dùng tham khảo' },
  { ten: 'tac_dung_phu', nhan: 'Tác dụng phụ' },
  { ten: 'than_trong', nhan: 'Thận trọng' },
  { ten: 'tuong_tac_thuoc', nhan: 'Tương tác thuốc' },
  { ten: 'phu_nu_co_thai_cho_con_bu', nhan: 'Phụ nữ có thai, cho con bú' },
  { ten: 'tre_em', nhan: 'Trẻ em' },
  { ten: 'qua_lieu_xu_tri', nhan: 'Quá liều và xử trí' },
  { ten: 'bao_quan', nhan: 'Bảo quản' },
] as const

export type TenTruongVanBan = (typeof TRUONG_VAN_BAN)[number]['ten']
export type TenTruong = TenTruongVanBan | 'file_hdsd_url'

/** Mọi ô của form là chuỗi (rỗng nghĩa là không có), giống `GiaTriFormDanhMuc`. */
export type GiaTriNoiDung = Record<TenTruong, string>

export const TRUONG_TOAN_BO: readonly { ten: TenTruong; nhan: string }[] = [
  ...TRUONG_VAN_BAN,
  { ten: 'file_hdsd_url', nhan: 'Tờ hướng dẫn sử dụng gốc' },
]

export const NOI_DUNG_TRONG: GiaTriNoiDung = Object.fromEntries(TRUONG_TOAN_BO.map((t) => [t.ten, ''])) as GiaTriNoiDung

export function giaTriTuPhienBan(p: PhienBanNoiDung | undefined): GiaTriNoiDung {
  if (!p) return { ...NOI_DUNG_TRONG }
  return Object.fromEntries(TRUONG_TOAN_BO.map((t) => [t.ten, p[t.ten] ?? ''])) as GiaTriNoiDung
}

/** Số phiên bản mới nhất (mọi trạng thái, kể cả đã lưu trữ), hoặc `null` nếu chưa có: giá trị `phien_ban_co_so` gửi lên. */
export function phienBanCoSo(cac: readonly PhienBanNoiDung[]): number | null {
  return cac.length === 0 ? null : Math.max(...cac.map((p) => p.phien_ban))
}

/**
 * Bản điền sẵn vào form: bản còn hiệu lực (nháp hoặc đang hiển thị) có số lớn nhất, cùng bản mà backend dùng để chặn bản
 * trùng. Bản nháp CŨ hơn bản đang hiển thị không được chọn: điền từ nó là kéo nội dung về một bản đã lỗi thời.
 */
export function banDienSan(cac: readonly PhienBanNoiDung[]): PhienBanNoiDung | undefined {
  return [...cac].sort((a, b) => b.phien_ban - a.phien_ban).find((p) => p.trang_thai !== 'luu_tru')
}

export function noiDungRaApi(g: GiaTriNoiDung, coSo: number | null): NoiDungVao {
  return {
    phien_ban_co_so: coSo,
    ...Object.fromEntries(TRUONG_VAN_BAN.map((t) => [t.ten, chuoiHoacNull(g[t.ten], true)])),
    file_hdsd_url: chuoiHoacNull(g.file_hdsd_url),
  }
}

/** Lỗi theo ô, cùng quy tắc với backend (`schemas_noi_dung.py`); rỗng nếu hợp lệ. */
export function kiemTraNoiDung(g: GiaTriNoiDung): Partial<Record<TenTruong, string>> {
  const loi: Partial<Record<TenTruong, string>> = {}
  for (const t of TRUONG_VAN_BAN) {
    const l = loiVanBan(g[t.ten], TOI_DA_KY_TU, true)
    if (l) loi[t.ten] = l
  }
  const url = loiDuongDan(g.file_hdsd_url)
  if (url) loi.file_hdsd_url = url
  return loi
}

/** Hai giá trị giống nhau theo cách backend so (trống = `null`, cắt đầu cuối). */
export function giongNhau(a: string | null | undefined, b: string | null | undefined): boolean {
  return (a ?? '').trim() === (b ?? '').trim()
}

export interface DongSoSanh {
  ten: TenTruong
  nhan: string
  truoc: string | null
  sau: string | null
  khac: boolean
}

/** So từng trường của hai phiên bản (`truoc` là bản cũ, `sau` là bản mới). */
export function soSanh(truoc: PhienBanNoiDung, sau: PhienBanNoiDung): DongSoSanh[] {
  return TRUONG_TOAN_BO.map((t) => ({
    ten: t.ten,
    nhan: t.nhan,
    truoc: truoc[t.ten],
    sau: sau[t.ten],
    khac: !giongNhau(truoc[t.ten], sau[t.ten]),
  }))
}

/** Form giống bản gốc (không thay đổi gì) thì không cho lưu: backend cũng từ chối bản trùng. */
export function coThayDoi(g: GiaTriNoiDung, goc: GiaTriNoiDung): boolean {
  return TRUONG_TOAN_BO.some((t) => !giongNhau(g[t.ten], goc[t.ten]))
}
