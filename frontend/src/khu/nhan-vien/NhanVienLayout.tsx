import { Result } from 'antd'
import { Navigate, useLocation } from 'react-router-dom'
import { KhungNoiBo } from '../../components/KhungNoiBo'
import { trangDauTienDuocPhep } from '../../lib/dieuHuong'
import { DUONG_DANG_NHAP_NOI_BO, DUONG_TAI_KHOAN_NOI_BO } from '../../lib/hoSoNoiBo'
import { usePhien } from '../../stores/phien'
import { MUC_NHAN_VIEN } from './menu'

/** Layout khu nhân viên (dược sĩ, kho). Chưa đăng nhập nội bộ thì về trang đăng nhập; Admin được đưa sang khu quản trị. */
export default function NhanVienLayout() {
  const { loai, hoSo, phaiDoiMatKhau } = usePhien()
  const vitri = useLocation()
  if (loai !== 'noi_bo') {
    return <Navigate to={DUONG_DANG_NHAP_NOI_BO} replace state={{ tu: vitri.pathname + vitri.search }} />
  }
  if (phaiDoiMatKhau) return <Navigate to={DUONG_TAI_KHOAN_NOI_BO} replace />
  if (hoSo?.vaiTro === 'ADMIN') return <Navigate to="/quan-tri" replace />
  return <KhungNoiBo goc="/nhan-vien" tieuDe="Nhà thuốc · Nhân viên" muc={MUC_NHAN_VIEN} />
}

/** Trang đầu của khu: chuyển tới mục menu đầu tiên người dùng có quyền. */
export function TrangDauNhanVien() {
  const quyen = usePhien((s) => s.quyen)
  const dau = trangDauTienDuocPhep(MUC_NHAN_VIEN, quyen)
  if (dau) return <Navigate to={`/nhan-vien${dau}`} replace />
  return (
    <Result
      status="warning"
      title="Tài khoản chưa được cấp quyền nào"
      subTitle="Liên hệ quản trị viên để được cấp quyền sử dụng các chức năng."
    />
  )
}
