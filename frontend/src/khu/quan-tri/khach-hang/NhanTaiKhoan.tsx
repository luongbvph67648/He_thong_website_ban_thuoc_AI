import { Space, Tag } from 'antd'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { dangKhoaTam, type TrangThaiTaiKhoanKhach } from './khach'

export function NhanTaiKhoan({ khach }: { khach: TrangThaiTaiKhoanKhach }) {
  return (
    <Space size={4} wrap>
      {khach.trang_thai === 'bi_khoa' ? <Tag color="red">Bị khóa</Tag> : <Tag color="green">Hoạt động</Tag>}
      {dangKhoaTam(khach) && <Tag color="orange">Khóa tạm đến {dinhDangNgay(khach.khoa_den, 'ngayGio')}</Tag>}
    </Space>
  )
}
