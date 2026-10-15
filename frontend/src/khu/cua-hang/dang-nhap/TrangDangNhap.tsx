import { Alert, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChoDoiLai, thongDiepChung } from '../../../api/goi'
import { duongTiepTheo } from '../../../lib/chuyenHuong'
import { usePhien } from '../../../stores/phien'

interface FormDangNhap {
  ten_dang_nhap: string
  mat_khau: string
}

/** Đăng nhập khách (KVL10) bằng số điện thoại hoặc email. Đăng nhập xong quay lại trang trong `?tiep=` (nếu hợp lệ). */
export default function TrangDangNhap() {
  const [tham] = useSearchParams()
  const dich = duongTiepTheo(tham.get('tiep'))
  const khachDaDangNhap = usePhien((s) => s.loai === 'khach')
  const [dangGui, setDangGui] = useState(false)
  const [thongBao, setThongBao] = useState<string | null>(null)
  const [form] = Form.useForm<FormDangNhap>()

  if (khachDaDangNhap) return <Navigate to={dich} replace />

  async function submit(gia_tri: FormDangNhap) {
    if (dangGui) return
    setDangGui(true)
    setThongBao(null)
    const kq = await goi(() =>
      api.POST('/api/v1/auth/dang-nhap', {
        body: { ten_dang_nhap: gia_tri.ten_dang_nhap.trim(), mat_khau: gia_tri.mat_khau },
      }),
    )
    setDangGui(false)
    if (kq.ok) {
      const { access_token, khach_hang } = kq.data
      usePhien.getState().dangNhap({
        accessToken: access_token,
        loai: 'khach',
        hoSo: { id: khach_hang.id, hoTen: khach_hang.ho_ten },
        quyen: {},
      })
      return // `khachDaDangNhap` đổi nên trang tự chuyển tới `dich`
    }
    form.setFieldValue('mat_khau', '')
    const loi = kq.loi
    setThongBao(loi && (loi.ma_loi === 'TAI_KHOAN_BI_KHOA' || loi.ma_loi === 'QUA_GIOI_HAN') ? thongDiepChoDoiLai(loi) : thongDiepChung(loi))
  }

  return (
    <Card style={{ maxWidth: 420, margin: '16px auto' }}>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        Đăng nhập
      </Typography.Title>
      {thongBao && <Alert type="error" showIcon title={thongBao} style={{ marginBottom: 16 }} />}
      <Form form={form} layout="vertical" onFinish={submit} requiredMark={false}>
        <Form.Item name="ten_dang_nhap" label="Số điện thoại hoặc email" rules={[{ required: true, whitespace: true, message: 'Vui lòng nhập số điện thoại hoặc email' }]}>
          <Input autoComplete="username" />
        </Form.Item>
        <Form.Item name="mat_khau" label="Mật khẩu" rules={[{ required: true, message: 'Vui lòng nhập mật khẩu' }]}>
          <Input.Password autoComplete="current-password" />
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={dangGui}>
          Đăng nhập
        </Button>
      </Form>
      <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <Link to="/quen-mat-khau">Quên mật khẩu?</Link>
        <span>
          Chưa có tài khoản? <Link to="/dang-ky">Đăng ký</Link>
        </span>
      </div>
    </Card>
  )
}
