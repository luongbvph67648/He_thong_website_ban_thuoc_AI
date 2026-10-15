import { Alert, Button, Card, Form, Input, Spin, Typography } from 'antd'
import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api } from '../../api/client'
import { goi, thongDiepChoDoiLai, thongDiepChung } from '../../api/goi'
import { duongTiepTheo } from '../../lib/chuyenHuong'
import { duongSauDangNhap } from '../../lib/dieuHuong'
import { DUONG_TAI_KHOAN_NOI_BO, phienTuNhanVien } from '../../lib/hoSoNoiBo'
import { usePhien } from '../../stores/phien'

interface FormDangNhap {
  email: string
  mat_khau: string
}

/**
 * Đăng nhập nội bộ dùng chung cho dược sĩ, kho và Admin (NV01, spec 09 mục 1). Sau khi đăng nhập: về trang đang định
 * vào (`state.tu`, chỉ nhận đường dẫn nội bộ), nếu không thì Admin vào `/quan-tri`, còn lại vào `/nhan-vien`. Tài khoản
 * còn bị bắt đổi mật khẩu thì sang trang tài khoản để đổi trước.
 */
export default function TrangDangNhapNoiBo() {
  const vitri = useLocation()
  const { loai, hoSo, phaiDoiMatKhau, daKhoiPhuc } = usePhien()
  const [dangGui, setDangGui] = useState(false)
  const [thongBao, setThongBao] = useState<string | null>(null)
  const [form] = Form.useForm<FormDangNhap>()

  // Đang lấy lại phiên khi tải trang: chờ xong mới quyết định hiện form hay chuyển đi, tránh nhấp nháy.
  if (!daKhoiPhuc) {
    return (
      <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh' }}>
        <Spin aria-label="Đang kiểm tra phiên đăng nhập" />
      </div>
    )
  }
  if (loai === 'noi_bo') {
    const tu = duongTiepTheo((vitri.state as { tu?: string } | null)?.tu ?? null, '')
    return <Navigate to={phaiDoiMatKhau ? DUONG_TAI_KHOAN_NOI_BO : tu || duongSauDangNhap(hoSo?.vaiTro)} replace />
  }

  async function submit(gia_tri: FormDangNhap) {
    if (dangGui) return
    setDangGui(true)
    setThongBao(null)
    const kq = await goi(() =>
      api.POST('/api/v1/noi-bo/auth/dang-nhap', { body: { email: gia_tri.email.trim(), mat_khau: gia_tri.mat_khau } }),
    )
    setDangGui(false)
    if (kq.ok) {
      usePhien.getState().dangNhap({ accessToken: kq.data.access_token, loai: 'noi_bo', ...phienTuNhanVien(kq.data.nhan_vien) })
      return // `loai` đổi nên trang tự chuyển đi
    }
    form.setFieldValue('mat_khau', '')
    const loi = kq.loi
    setThongBao(loi && (loi.ma_loi === 'TAI_KHOAN_BI_KHOA' || loi.ma_loi === 'QUA_GIOI_HAN') ? thongDiepChoDoiLai(loi) : thongDiepChung(loi))
  }

  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 16 }}>
      <Card style={{ width: 420, maxWidth: '100%' }}>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          Đăng nhập nội bộ
        </Typography.Title>
        {thongBao && <Alert type="error" showIcon title={thongBao} style={{ marginBottom: 16 }} />}
        <Form form={form} layout="vertical" onFinish={submit} requiredMark={false}>
          <Form.Item
            name="email"
            label="Email"
            rules={[{ required: true, whitespace: true, message: 'Vui lòng nhập email' }]}
          >
            <Input autoComplete="username" inputMode="email" />
          </Form.Item>
          <Form.Item name="mat_khau" label="Mật khẩu" rules={[{ required: true, message: 'Vui lòng nhập mật khẩu' }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={dangGui}>
            Đăng nhập
          </Button>
        </Form>
        <Typography.Paragraph type="secondary" style={{ marginTop: 16, marginBottom: 0 }}>
          Tài khoản nội bộ do quản trị viên cấp. Quên mật khẩu thì liên hệ quản trị viên để được đặt lại.
        </Typography.Paragraph>
      </Card>
    </div>
  )
}
