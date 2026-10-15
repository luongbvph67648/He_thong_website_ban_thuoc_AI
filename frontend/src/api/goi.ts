import { laLoiApi, type LoiApi } from './loi'

export type KetQuaGoi<T> = { ok: true; data: T } | { ok: false; loi: LoiApi | null }

/**
 * Gọi API và quy mọi kết quả (kể cả lỗi mạng) về một dạng; `loi = null` nghĩa là không nhận được phản hồi hợp lệ.
 *
 * Phản hồi 2xx không có thân (204 của xóa mềm, đăng xuất) làm openapi-fetch trả `data: undefined`, nên thành công phải
 * dựa vào `response.ok` chứ không chỉ vào `data`. Ngược lại phản hồi lỗi không có thân cho `error = ''` (falsy), nên
 * không được suy ra thành công từ việc `error` rỗng.
 */
export async function goi<T>(
  thucHien: () => Promise<{ data?: T; error?: unknown; response?: Pick<Response, 'ok'> }>,
): Promise<KetQuaGoi<T>> {
  try {
    const { data, error, response } = await thucHien()
    if (data !== undefined && !error) return { ok: true, data }
    if (data === undefined && !error && response?.ok) return { ok: true, data: undefined as T }
    return { ok: false, loi: laLoiApi(error) ? error : null }
  } catch {
    return { ok: false, loi: null }
  }
}

export function thongDiepChung(loi: LoiApi | null): string {
  return loi ? loi.thong_diep : 'Không kết nối được máy chủ, vui lòng thử lại.'
}

/** Lỗi có `chi_tiet.thu_lai_sau_giay` (giới hạn tần suất, khóa tạm): nói rõ phải chờ bao lâu. */
export function thongDiepChoDoiLai(loi: LoiApi): string {
  const giay = (loi.chi_tiet as { thu_lai_sau_giay?: number } | null)?.thu_lai_sau_giay
  return giay ? `${loi.thong_diep}. Hãy thử lại sau ${Math.ceil(giay / 60)} phút.` : loi.thong_diep
}

/** Lỗi OTP sai kèm số lần thử còn lại (`chi_tiet.so_lan_con_lai`). */
export function thongDiepOtpSai(loi: LoiApi): string {
  const conLai = (loi.chi_tiet as { so_lan_con_lai?: number } | null)?.so_lan_con_lai
  return conLai && conLai > 0 ? `${loi.thong_diep}. Bạn còn ${conLai} lần thử.` : loi.thong_diep
}
