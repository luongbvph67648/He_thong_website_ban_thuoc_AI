/** Kiểm tra ô nhập của AD03/AD05 phía giao diện, cùng quy tắc với backend (`core/kieu_du_lieu.py`; test dùng chung bảng ca). */

export const DO_DAI_DUONG_DAN_TOI_DA = 500

// eslint-disable-next-line no-control-regex
const KY_TU_DIEU_KHIEN = /[\u0000-\u001f\u007f]/
const DUONG_DAN = /^(https?:\/\/\S+|\/(?!\/)\S*)$/

/** Bỏ khoảng trắng đầu cuối và gộp khoảng trắng liên tiếp (như backend). */
export function gonTen(s: string): string {
  return s.trim().split(/\s+/).filter(Boolean).join(' ')
}

/** Lỗi của ô tên bắt buộc, hoặc `null` nếu hợp lệ. */
export function loiTen(s: string, toiDa: number): string | null {
  const ten = gonTen(s)
  if (ten === '') return 'Vui lòng nhập tên'
  if (KY_TU_DIEU_KHIEN.test(ten)) return 'Không được chứa ký tự điều khiển'
  if (ten.length > toiDa) return `Tối đa ${toiDa} ký tự`
  return null
}

/** Lỗi của ô đường dẫn tùy chọn (trống là hợp lệ): chỉ nhận `/...` hoặc `http(s)://...`. */
export function loiDuongDan(s: string): string | null {
  const v = s.trim()
  if (v === '') return null
  if (v.length > DO_DAI_DUONG_DAN_TOI_DA || KY_TU_DIEU_KHIEN.test(v) || !DUONG_DAN.test(v)) {
    return `Đường dẫn phải bắt đầu bằng / hoặc http(s)://, không có khoảng trắng, tối đa ${DO_DAI_DUONG_DAN_TOI_DA} ký tự`
  }
  return null
}

/** Lỗi của ô văn bản tùy chọn (trống là hợp lệ). `nhieuDong` cho phép xuống dòng và tab. */
export function loiVanBan(s: string, toiDa: number, nhieuDong = false): string | null {
  const v = nhieuDong ? s.trim() : gonTen(s)
  if (v === '') return null
  // eslint-disable-next-line no-control-regex
  if ((nhieuDong ? /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/ : KY_TU_DIEU_KHIEN).test(v)) return 'Không được chứa ký tự điều khiển'
  if (v.length > toiDa) return `Tối đa ${toiDa} ký tự`
  return null
}

/** Chuỗi gửi lên: trống thành `null` (xóa giá trị), ngược lại đã gọn. */
export function chuoiHoacNull(s: string | undefined | null, nhieuDong = false): string | null {
  const v = nhieuDong ? (s ?? '').trim() : gonTen(s ?? '')
  return v === '' ? null : v
}
