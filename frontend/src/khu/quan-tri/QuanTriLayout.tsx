import { Navigate, useLocation } from 'react-router-dom'
import { KhungNoiBo } from '../../components/KhungNoiBo'
import { Trang403 } from '../../components/Trang403'
import { usePhien } from '../../stores/phien'
import { MUC_QUAN_TRI } from './menu'

/** Layout khu quản trị: chỉ vai trò ADMIN. Mỗi trang con vẫn kiểm tra mã quyền riêng. */
export default function QuanTriLayout() {
  const { loai, hoSo } = usePhien()
  const vitri = useLocation()
  if (loai !== 'noi_bo') {
    return <Navigate to="/nhan-vien/dang-nhap" replace state={{ tu: vitri.pathname + vitri.search }} />
  }
  if (hoSo?.vaiTro !== 'ADMIN') return <Trang403 />
  return <KhungNoiBo goc="/quan-tri" tieuDe="Nhà thuốc · Quản trị" muc={MUC_QUAN_TRI} />
}
