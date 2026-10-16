import { Descriptions, Space, Spin, Typography } from 'antd'
import { Link, Navigate } from 'react-router-dom'
import { usePhien } from '../../../stores/phien'
import SoDiaChi from './SoDiaChi'

/** KTV01: tài khoản của tôi (sổ địa chỉ; sửa hồ sơ và đổi mật khẩu là việc phát sinh sau T4.1). */
export default function TrangTaiKhoan() {
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const khach = usePhien((s) => s.loai === 'khach')
  const hoSo = usePhien((s) => s.hoSo)
  if (!daKhoiPhuc) return <Spin />
  if (!khach) return <Navigate to="/dang-nhap?tiep=/tai-khoan" replace />
  return (
    <Space orientation="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Tài khoản của tôi</Typography.Title>
      <Descriptions bordered size="small" column={1} items={[{ key: 'ten', label: 'Họ tên', children: hoSo?.hoTen }]} />
      <Link to="/tai-khoan/don-hang">Đơn hàng của tôi</Link>
      <Link to="/tai-khoan/doi-tra">Đổi trả của tôi</Link>
      <Link to="/tai-khoan/danh-gia">Đánh giá và hỏi đáp</Link>
      <Link to="/tai-khoan/don-thuoc">Đơn thuốc của tôi</Link>
      <Link to="/tai-khoan/suc-khoe">Hồ sơ sức khỏe</Link>
      <SoDiaChi />
    </Space>
  )
}
