import { Navigate, useLocation } from 'react-router-dom'
import { KhungNoiBo } from '../../components/KhungNoiBo'
import { Trang403 } from '../../components/Trang403'
import { DUONG_DANG_NHAP_NOI_BO, DUONG_TAI_KHOAN_NOI_BO } from '../../lib/hoSoNoiBo'
import { usePhien } from '../../stores/phien'
import { MUC_QUAN_TRI } from './menu'

/** Layout khu quản trị: chỉ vai trò ADMIN. Mỗi trang con vẫn kiểm tra mã quyền riêng. */
export default function QuanTriLayout() {
  const { loai, hoSo, phaiDoiMatKhau } = usePhien()
  const vitri = useLocation()
  if (loai !== 'noi_bo') {
    return <Navigate to={DUONG_DANG_NHAP_NOI_BO} replace state={{ tu: vitri.pathname + vitri.search }} />
  }
  if (phaiDoiMatKhau) return <Navigate to={DUONG_TAI_KHOAN_NOI_BO} replace />
  if (hoSo?.vaiTro !== 'ADMIN') return <Trang403 />
  return <KhungNoiBo goc="/quan-tri" tieuDe="Nhà thuốc · Quản trị" muc={MUC_QUAN_TRI} />
}
