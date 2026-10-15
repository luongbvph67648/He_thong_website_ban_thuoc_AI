/** Tối thiểu 8 ký tự, có ít nhất một chữ và một số: giống backend (`core/bao_mat.py`, spec 06 mục 3). */
export const MAT_KHAU_TOI_THIEU = 8

export function matKhauDuManh(mk: string): boolean {
  return [...mk].length >= MAT_KHAU_TOI_THIEU && /\p{L}/u.test(mk) && /\p{Nd}/u.test(mk)
}
