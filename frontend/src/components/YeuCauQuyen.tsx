import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { DUONG_DANG_NHAP_NOI_BO, DUONG_TAI_KHOAN_NOI_BO } from '../lib/hoSoNoiBo'
import { coMotTrong, type MucYeuCau } from '../lib/quyen'
import { usePhien } from '../stores/phien'
import { Trang403 } from './Trang403'

interface Props {
  /** Mã quyền (spec 03). Nhiều mã: có một trong số đó là qua. */
  ma: string | readonly string[]
  /** `day_du` (mặc định): chỉ quyền đầy đủ; `xem`: cả quyền chỉ xem. */
  muc?: MucYeuCau
  /**
   * `route` (mặc định): bọc trang. Chưa đăng nhập nội bộ thì chuyển tới đăng nhập, thiếu quyền thì hiện 403.
   * `nut`: bọc nút/khối thao tác. Thiếu quyền thì ẩn hẳn.
   */
  kieu?: 'route' | 'nut'
  children: ReactNode
}

/**
 * Guard theo quyền cho khu nội bộ. Chỉ là lớp phụ trên giao diện: backend luôn kiểm tra lại mọi lời gọi.
 * Phiên của khách (`loai = khach`) không được coi là đã đăng nhập nội bộ.
 */
export function YeuCauQuyen({ ma, muc = 'day_du', kieu = 'route', children }: Props) {
  const { loai, quyen, phaiDoiMatKhau } = usePhien()
  const vitri = useLocation()
  const daDangNhap = loai === 'noi_bo'
  const duocPhep = daDangNhap && coMotTrong(quyen, typeof ma === 'string' ? [ma] : ma, muc)

  if (kieu === 'nut') return duocPhep ? <>{children}</> : null
  if (!daDangNhap) {
    return <Navigate to={DUONG_DANG_NHAP_NOI_BO} replace state={{ tu: vitri.pathname + vitri.search }} />
  }
  if (phaiDoiMatKhau) return <Navigate to={DUONG_TAI_KHOAN_NOI_BO} replace />
  return duocPhep ? <>{children}</> : <Trang403 />
}
