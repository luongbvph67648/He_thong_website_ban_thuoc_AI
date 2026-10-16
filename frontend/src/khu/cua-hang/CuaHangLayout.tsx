import { LogoutOutlined, UserOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { Button, Layout, Skeleton, Space } from 'antd'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { dangXuatKhach } from '../../api/dangXuat'
import { ChuongThongBao } from '../../components/ChuongThongBao'
import { usePhien } from '../../stores/phien'
import { ChanTrang } from './ChanTrang'
import { MiniGioHang } from './gio-hang/MiniGioHang'
import { useGopGioKhiDangNhap } from './gio-hang/gioHang'
import { MenuDanhMuc } from './MenuDanhMuc'
import { OTimKiem } from './OTimKiem'

const { Header, Content } = Layout

/**
 * Layout khu cửa hàng (`/`): header gồm logo, tìm kiếm, giỏ hàng, tài khoản, kèm thanh danh mục 3 cấp. Widget chat nổi
 * (T6.x) sẽ gắn vào đây khi có dữ liệu.
 */
export default function CuaHangLayout() {
  const khachDaDangNhap = usePhien((s) => s.loai === 'khach')
  const hoTen = usePhien((s) => s.hoSo?.hoTen)
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const dieuHuong = useNavigate()
  useGopGioKhiDangNhap()
  const queryClient = useQueryClient()

  async function dangXuat() {
    await dangXuatKhach()
    queryClient.clear() // bỏ dữ liệu của khách vừa đăng xuất khỏi bộ nhớ đệm
    dieuHuong('/')
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          background: '#fff',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          flexWrap: 'wrap',
          height: 'auto',
          padding: '8px 16px',
        }}
      >
        <Link to="/" style={{ fontSize: 20, fontWeight: 600, whiteSpace: 'nowrap' }}>
          Nhà thuốc AI
        </Link>
        <OTimKiem />
        <Space size="large">
          <MiniGioHang />
          {!daKhoiPhuc ? (
            <span role="status" aria-label="Đang tải tài khoản">
              <Skeleton.Button active size="small" />
            </span>
          ) : khachDaDangNhap ? (
            <Space>
              <ChuongThongBao phamVi="khach" />
              <Link to="/tai-khoan">
                <UserOutlined /> {hoTen ?? 'Tài khoản'}
              </Link>
              <Button type="link" icon={<LogoutOutlined />} onClick={() => void dangXuat()} style={{ padding: 0 }}>
                Đăng xuất
              </Button>
            </Space>
          ) : (
            <Link to="/dang-nhap">
              <UserOutlined /> Đăng nhập
            </Link>
          )}
        </Space>
      </Header>
      <MenuDanhMuc />
      <Content style={{ padding: 16, maxWidth: 1200, width: '100%', margin: '0 auto' }}>
        <Outlet />
      </Content>
      <ChanTrang />
    </Layout>
  )
}
