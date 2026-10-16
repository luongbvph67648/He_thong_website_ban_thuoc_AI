/** Kiểm tra ô nhập của AD03/AD05 phía giao diện, cùng quy tắc với backend (`core/kieu_du_lieu.py`; test dùng chung bảng ca). */

export const DO_DAI_DUONG_DAN_TOI_DA = 500
const THONG_DIEP_KY_TU_CAM = 'Không được chứa ký tự điều khiển hoặc ký tự vô hình'

/**
 * Ký tự không được có trong dữ liệu nhập (cùng quy tắc với backend `_co_ky_tu_dieu_khien`): `Cc` điều khiển (NUL làm
 * PostgreSQL báo 500), `Cf` định dạng vô hình (U+200B, bidi...: hai tên trông giống hệt mà không bị coi là trùng), `Cs`
 * surrogate đơn lẻ (không mã hóa được UTF-8). Cặp surrogate hợp lệ (emoji) là một ký tự thường, không bị bắt.
 */
const KY_TU_CAM = /[\p{Cc}\p{Cf}\p{Cs}]/u
const DUONG_DAN = /^(https?:\/\/\S+|\/(?![/\\])\S*)$/ // `/\host` được trình duyệt hiểu như `//host`

const coKyTuCam = (s: string, choPhep = '') => KY_TU_CAM.test(choPhep ? s.replace(new RegExp(`[${choPhep}]`, 'g'), '') : s)

/** Bỏ khoảng trắng đầu cuối và gộp khoảng trắng liên tiếp (như backend). */
export function gonTen(s: string): string {
  return s.trim().split(/\s+/).filter(Boolean).join(' ')
}

/** Lỗi của ô tên bắt buộc, hoặc `null` nếu hợp lệ. */
export function loiTen(s: string, toiDa: number): string | null {
  const ten = gonTen(s)
  if (ten === '') return 'Vui lòng nhập tên'
  if (coKyTuCam(ten)) return THONG_DIEP_KY_TU_CAM
  if (ten.length > toiDa) return `Tối đa ${toiDa} ký tự`
  return null
}

/** Lỗi của ô đường dẫn tùy chọn (trống là hợp lệ): chỉ nhận `/...` hoặc `http(s)://...`. */
export function loiDuongDan(s: string): string | null {
  const v = s.trim()
  if (v === '') return null
  if (v.length > DO_DAI_DUONG_DAN_TOI_DA || coKyTuCam(v) || !DUONG_DAN.test(v)) {
    return `Đường dẫn phải bắt đầu bằng / hoặc http(s)://, không có khoảng trắng, tối đa ${DO_DAI_DUONG_DAN_TOI_DA} ký tự`
  }
  return null
}

/** Lỗi của ô văn bản tùy chọn (trống là hợp lệ). `nhieuDong` cho phép xuống dòng và tab. */
export function loiVanBan(s: string, toiDa: number, nhieuDong = false): string | null {
  const v = nhieuDong ? s.trim() : gonTen(s)
  if (v === '') return null
  if (coKyTuCam(v, nhieuDong ? '\\n\\r\\t' : '')) return THONG_DIEP_KY_TU_CAM
  if (v.length > toiDa) return `Tối đa ${toiDa} ký tự`
  return null
}

/** Chuỗi gửi lên: trống thành `null` (xóa giá trị), ngược lại đã gọn. */
export function chuoiHoacNull(s: string | undefined | null, nhieuDong = false): string | null {
  const v = nhieuDong ? (s ?? '').trim() : gonTen(s ?? '')
  return v === '' ? null : v
}
