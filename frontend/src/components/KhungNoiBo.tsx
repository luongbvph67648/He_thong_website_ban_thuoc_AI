import { LogoutOutlined, UserOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { Button, Dropdown, Layout, Menu, Space, Typography } from 'antd'
import { useMemo } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { dangXuatNoiBo } from '../api/dangXuat'
import type { MucDieuHuong } from '../lib/dieuHuong'
import { DUONG_DANG_NHAP_NOI_BO, DUONG_TAI_KHOAN_NOI_BO } from '../lib/hoSoNoiBo'
import { usePhien } from '../stores/phien'
import { ChuongThongBao } from './ChuongThongBao'
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
  const vitri = useLocation()
  const dieuHuong = useNavigate()
  const queryClient = useQueryClient()
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
            <ChuongThongBao />
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'tai-khoan',
                    icon: <UserOutlined />,
                    label: 'Hồ sơ và đổi mật khẩu',
                    onClick: () => dieuHuong(DUONG_TAI_KHOAN_NOI_BO),
                  },
                  {
                    key: 'dang-xuat',
                    icon: <LogoutOutlined />,
                    label: 'Đăng xuất',
                    onClick: async () => {
                      await dangXuatNoiBo()
                      queryClient.clear() // bỏ dữ liệu của phiên vừa đăng xuất khỏi bộ nhớ đệm
                      dieuHuong(DUONG_DANG_NHAP_NOI_BO)
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
