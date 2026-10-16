/** Dữ liệu và hàm thuần của màn tương tác hoạt chất (DS10). */
import type { components } from '../../../api/schema'
import type { LuaChon } from '../../../components/ChonDuLieuChung'
import { chuoiHoacNull, loiVanBan } from '../../../lib/duLieuChung'

export type TuongTac = components['schemas']['TuongTacDoc']
export type MucDoTuongTac = components['schemas']['MucDoTuongTac']

export const KHOA_QUERY_TUONG_TAC = ['noi-bo', 'tuong-tac'] as const

/** Thứ tự nặng → nhẹ, cùng thứ tự backend sắp xếp. */
export const MUC_DO: readonly MucDoTuongTac[] = ['chong_chi_dinh', 'nghiem_trong', 'trung_binh', 'nhe']

export interface GiaTriTuongTac {
  hoat_chat_1: LuaChon | null
  hoat_chat_2: LuaChon | null
  muc_do: MucDoTuongTac | undefined
  co_che: string
  khuyen_cao: string
  nguon_tham_khao: string
}

export const TUONG_TAC_TRONG: GiaTriTuongTac = {
  hoat_chat_1: null,
  hoat_chat_2: null,
  muc_do: undefined,
  co_che: '',
  khuyen_cao: '',
  nguon_tham_khao: '',
}

export function giaTriTuBanGhi(t: TuongTac): GiaTriTuongTac {
  return {
    hoat_chat_1: { value: t.hoat_chat_a_id, label: t.ten_hoat_chat_a },
    hoat_chat_2: { value: t.hoat_chat_b_id, label: t.ten_hoat_chat_b },
    muc_do: t.muc_do,
    co_che: t.co_che ?? '',
    khuyen_cao: t.khuyen_cao,
    nguon_tham_khao: t.nguon_tham_khao ?? '',
  }
}

export type LoiTuongTac = Partial<Record<keyof GiaTriTuongTac, string>>

/** Lỗi theo ô, cùng quy tắc với backend (`schemas_tuong_tac.py`, `tuong_tac.tao`); rỗng nếu hợp lệ. */
export function kiemTraTuongTac(g: GiaTriTuongTac): LoiTuongTac {
  const loi: LoiTuongTac = {}
  if (!g.hoat_chat_1) loi.hoat_chat_1 = 'Vui lòng chọn hoạt chất thứ nhất'
  if (!g.hoat_chat_2) loi.hoat_chat_2 = 'Vui lòng chọn hoạt chất thứ hai'
  else if (g.hoat_chat_1 && g.hoat_chat_1.value === g.hoat_chat_2.value) loi.hoat_chat_2 = 'Hai hoạt chất phải khác nhau'
  if (!g.muc_do) loi.muc_do = 'Vui lòng chọn mức độ'
  const coChe = loiVanBan(g.co_che, 2000, true)
  if (coChe) loi.co_che = coChe
  if (g.khuyen_cao.trim() === '') loi.khuyen_cao = 'Vui lòng nhập khuyến cáo'
  else {
    const kc = loiVanBan(g.khuyen_cao, 2000, true)
    if (kc) loi.khuyen_cao = kc
  }
  const nguon = loiVanBan(g.nguon_tham_khao, 255)
  if (nguon) loi.nguon_tham_khao = nguon
  return loi
}

/** Thân gửi lên cho phần nội dung (ô trống thành `null`). */
export function noiDungRaApi(g: GiaTriTuongTac) {
  return {
    muc_do: g.muc_do as MucDoTuongTac,
    co_che: chuoiHoacNull(g.co_che, true),
    khuyen_cao: g.khuyen_cao.trim(),
    nguon_tham_khao: chuoiHoacNull(g.nguon_tham_khao),
  }
}

/** Tên trường API của lỗi máy chủ → ô của form. */
export const O_THEO_TRUONG_API: Record<string, keyof GiaTriTuongTac> = {
  hoat_chat_1_id: 'hoat_chat_1',
  hoat_chat_2_id: 'hoat_chat_2',
  muc_do: 'muc_do',
  co_che: 'co_che',
  khuyen_cao: 'khuyen_cao',
  nguon_tham_khao: 'nguon_tham_khao',
}
