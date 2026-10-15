/** Kiểm tra quyền trên UI. Chỉ là lớp phụ: backend luôn kiểm tra lại (spec 03). */

export type MucQuyen = 'day_du' | 'chi_xem'
/** Quyền của người đang đăng nhập: mã quyền -> mức (`GET /api/v1/noi-bo/toi`). */
export type QuyenCuaToi = Record<string, MucQuyen>
/** Mức route/nút yêu cầu: `xem` nhận cả chỉ xem lẫn đầy đủ, `day_du` chỉ nhận đầy đủ (giống `yeu_cau_quyen`). */
export type MucYeuCau = 'xem' | 'day_du'

export function coQuyen(quyen: QuyenCuaToi, ma: string, muc: MucYeuCau = 'day_du'): boolean {
  const mucCoSan = Object.hasOwn(quyen, ma) ? quyen[ma] : undefined
  if (mucCoSan === undefined) return false
  return muc === 'xem' ? true : mucCoSan === 'day_du'
}

/** Qua nếu có ít nhất một mã trong danh sách (ví dụ mục menu cần `order.pick` hoặc `shipment.create`). */
export function coMotTrong(quyen: QuyenCuaToi, danhSachMa: readonly string[], muc: MucYeuCau = 'day_du'): boolean {
  return danhSachMa.some((ma) => coQuyen(quyen, ma, muc))
}
