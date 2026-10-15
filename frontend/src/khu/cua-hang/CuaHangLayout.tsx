import { LogoutOutlined, ShoppingCartOutlined, UserOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { Button, Input, Layout, Skeleton, Space, Typography } from 'antd'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { dangXuatKhach } from '../../api/dangXuat'
import { usePhien } from '../../stores/phien'

const { Header, Content, Footer } = Layout

/**
 * Layout khu cửa hàng (`/`): header gồm logo, tìm kiếm, giỏ hàng, tài khoản. Menu danh mục 3 cấp (cần API danh mục,
 * T2.x), widget chat nổi (T6.x) và số lượng trên giỏ hàng (T4.x) sẽ gắn vào đây khi có dữ liệu.
 */
export default function CuaHangLayout() {
  const khachDaDangNhap = usePhien((s) => s.loai === 'khach')
  const hoTen = usePhien((s) => s.hoSo?.hoTen)
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const dieuHuong = useNavigate()
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
        <Input.Search
          placeholder="Tìm thuốc, thực phẩm chức năng, thiết bị y tế…"
          allowClear
          style={{ flex: '1 1 240px', maxWidth: 560 }}
          onSearch={(q) => {
            const tu = q.trim()
            if (tu) dieuHuong(`/tim-kiem?q=${encodeURIComponent(tu)}`)
          }}
        />
        <Space size="large">
          <Link to="/gio-hang">
            <ShoppingCartOutlined /> Giỏ hàng
          </Link>
          {!daKhoiPhuc ? (
            <span role="status" aria-label="Đang tải tài khoản">
              <Skeleton.Button active size="small" />
            </span>
          ) : khachDaDangNhap ? (
            <Space>
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
      <Content style={{ padding: 16, maxWidth: 1200, width: '100%', margin: '0 auto' }}>
        <Outlet />
      </Content>
      <Footer style={{ textAlign: 'center' }}>
        <Space separator="·" wrap>
          <Link to="/bai-viet">Bài viết</Link>
          <Link to="/hoi-dap">Hỏi đáp</Link>
        </Space>
        <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
          Thông tin trên website chỉ mang tính tham khảo, không thay thế tư vấn của dược sĩ hoặc bác sĩ.
        </Typography.Paragraph>
      </Footer>
    </Layout>
  )
}
