import { BellOutlined, LogoutOutlined, UserOutlined } from '@ant-design/icons'
import { Badge, Button, Dropdown, Layout, Menu, Space, Typography } from 'antd'
import { useMemo } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import type { MucDieuHuong } from '../lib/dieuHuong'
import { usePhien } from '../stores/phien'
import { duongDayDu, xayMenu } from './xayMenu'

const { Sider, Header, Content } = Layout

interface Props {
  goc: '/nhan-vien' | '/quan-tri'
  tieuDe: string
  muc: readonly MucDieuHuong[]
}

/** Khung dùng chung cho khu nhân viên và khu quản trị: sider menu theo quyền, header (thông báo, tài khoản). */
export function KhungNoiBo({ goc, tieuDe, muc }: Props) {
  const quyen = usePhien((s) => s.quyen)
  const hoSo = usePhien((s) => s.hoSo)
  const dangXuat = usePhien((s) => s.dangXuat)
  const vitri = useLocation()
  const dieuHuong = useNavigate()
  const items = useMemo(() => xayMenu(goc, muc, quyen), [goc, muc, quyen])

  // Mục đang chọn: đường dẫn dài nhất là tiền tố của địa chỉ hiện tại (để trang con vẫn sáng mục cha).
  const dangChon = muc
    .map((m) => duongDayDu(goc, m.duong).replace(/\/:\w+$/, ''))
    .filter((d) => vitri.pathname === d || vitri.pathname.startsWith(`${d}/`))
    .sort((a, b) => b.length - a.length)[0]

  return (
    <Layout style={{ minHeight: '100vh', minWidth: 1280 }}>
      <Sider width={248} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '16px 20px' }}>
          <Typography.Text strong style={{ fontSize: 16 }}>
            {tieuDe}
          </Typography.Text>
        </div>
        <Menu mode="inline" items={items} selectedKeys={dangChon ? [dangChon] : []} style={{ borderInlineEnd: 0 }} />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            paddingInline: 24,
          }}
        >
          <Space size="large">
            <Badge count={0} showZero={false}>
              <BellOutlined aria-label="Thông báo" style={{ fontSize: 18 }} />
            </Badge>
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'dang-xuat',
                    icon: <LogoutOutlined />,
                    label: 'Đăng xuất',
                    onClick: () => {
                      dangXuat()
                      dieuHuong('/nhan-vien/dang-nhap')
                    },
                  },
                ],
              }}
            >
              <Button type="text" icon={<UserOutlined />}>
                {hoSo?.hoTen ?? 'Tài khoản'}
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
