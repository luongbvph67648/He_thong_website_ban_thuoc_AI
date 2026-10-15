/** Lỗi API theo định dạng thống nhất của backend (spec 06 mục 4). */
export interface LoiApi {
  ma_loi: string
  thong_diep: string
  chi_tiet: unknown
}

export function laLoiApi(gia: unknown): gia is LoiApi {
  if (typeof gia !== 'object' || gia === null) return false
  const g = gia as Record<string, unknown>
  return typeof g.ma_loi === 'string' && typeof g.thong_diep === 'string' && 'chi_tiet' in g
}

/**
 * Gắn lỗi vào từng trường của form: lỗi validate (`chi_tiet` là danh sách `{truong, loi}`) và lỗi trùng dữ liệu
 * (`chi_tiet = {truong}`). Lỗi khác trả bảng rỗng, người gọi hiện `thong_diep`.
 */
export function loiTheoTruong(loi: LoiApi): Record<string, string> {
  const ket: Record<string, string> = {}
  if (Array.isArray(loi.chi_tiet)) {
    for (const muc of loi.chi_tiet) {
      if (typeof muc === 'object' && muc !== null && 'truong' in muc && 'loi' in muc) {
        ket[String(muc.truong)] = String(muc.loi)
      }
    }
  } else if (typeof loi.chi_tiet === 'object' && loi.chi_tiet !== null && 'truong' in loi.chi_tiet) {
    ket[String(loi.chi_tiet.truong)] = loi.thong_diep
  }
  return ket
}
