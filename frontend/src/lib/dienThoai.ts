/**
 * Chuẩn hóa số di động Việt Nam về `0xxxxxxxxx`, giống backend (`core/dien_thoai.py`). Trả `null` nếu không hợp lệ.
 * Chỉ để báo lỗi sớm trên form: backend luôn kiểm tra lại.
 */
export function chuanHoaSdt(gia: string): string | null {
  let so = gia.trim().replace(/[ .-]/g, '')
  if (so.startsWith('+84')) so = `0${so.slice(3)}`
  else if (so.startsWith('84') && so.length === 11) so = `0${so.slice(2)}`
  return /^0[35789][0-9]{8}$/.test(so) ? so : null
}
