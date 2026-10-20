import { LogoutOutlined, UserOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { Button, Layout, Skeleton, Space } from 'antd'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { dangXuatKhach } from '../../api/dangXuat'
import WidgetChat from './chat/WidgetChat'
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
    <Layout className="cua-hang" style={{ minHeight: '100vh' }}>
      <div className="thanh-thong-tin-cua-hang">
        <div className="thanh-thong-tin-noi-dung">
          <span>Chăm sóc sức khỏe cho cả gia đình</span>
          <span className="thanh-thong-tin-diem">Tư vấn cùng dược sĩ</span>
          <Link to="/tai-khoan/don-hang">Theo dõi đơn hàng <span aria-hidden="true">→</span></Link>
        </div>
      </div>
      <Header
        className="dau-trang-cua-hang"
      >
        <Link to="/" className="thuong-hieu">
          <span className="thuong-hieu-icon" aria-hidden="true">
            <svg viewBox="0 0 48 48" focusable="false">
              <path className="dau-thap-y-te" d="M20 4h8v14h16v8H28v18h-8V26H4v-8h16z" />
              <path className="chen-hygeia" d="M15 29h18l-2 10H17zM13 29h22" />
              <path className="ran-hygeia" d="M24 29c-3-2-2-5 1-6 3-1 6 1 6 3 0 2-2 3-4 2-2-1-2-3 0-5l4-4c2-2 1-5-2-6-3-1-6 1-6 3 0 2 2 3 4 2 2-1 2-3 0-5l-1-1" />
              <circle className="ran-dau" cx="22.5" cy="10.5" r="1.2" />
            </svg>
          </span>
          <span className="thuong-hieu-chu"><strong>Nhà thuốc AI</strong><small>Khỏe an tâm mỗi ngày</small></span>
        </Link>
        <OTimKiem />
        <Space size="middle" className="hanh-dong-dau-trang">
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
            <Link className="nut-tai-khoan" to="/dang-nhap">
              <UserOutlined /> Đăng nhập
            </Link>
          )}
        </Space>
      </Header>
      <MenuDanhMuc />
      <div className="khung-trang-khach">
        <Content className="noi-dung-cua-hang" style={{ padding: 24, maxWidth: 1760, width: '100%', margin: '0 auto' }}>
          <Outlet />
        </Content>
      </div>
      <ChanTrang />
      <WidgetChat />
    </Layout>
  )
}
