import { ArrowLeftOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, Descriptions, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { goi, thongDiepChoDoiLai, thongDiepChung } from '../../api/goi'
import { loiTheoTruong } from '../../api/loi'
import { duongSauDangNhap } from '../../lib/dieuHuong'
import { chuanHoaSdt } from '../../lib/dienThoai'
import { DUONG_DANG_NHAP_NOI_BO, phienTuNhanVien } from '../../lib/hoSoNoiBo'
import { matKhauDuManh } from '../../lib/matKhau'
import { usePhien } from '../../stores/phien'

interface FormHoSo {
  ho_ten: string
  so_dien_thoai?: string
}

interface FormMatKhau {
  mat_khau_cu: string
  mat_khau_moi: string
  nhap_lai_mat_khau: string
}

/**
 * Tài khoản cá nhân của nhân viên (NV01, NV02), dùng chung cho cả ba vai trò: sửa họ tên/số điện thoại và đổi mật khẩu.
 * Khi `phaiDoiMatKhau` (lần đăng nhập đầu hoặc vừa được đặt lại) mọi trang nội bộ chuyển về đây và chỉ còn form đổi
 * mật khẩu cho tới khi đổi xong.
 */
export default function TrangTaiKhoanNoiBo() {
  const vitri = useLocation()
  const dieuHuong = useNavigate()
  const { message } = App.useApp()
  const { loai, hoSo, phaiDoiMatKhau } = usePhien()
  const [thongBaoHoSo, setThongBaoHoSo] = useState<string | null>(null)
  const [thongBaoMk, setThongBaoMk] = useState<string | null>(null)
  const [dangGuiHoSo, setDangGuiHoSo] = useState(false)
  const [dangGuiMk, setDangGuiMk] = useState(false)
  const [formHoSo] = Form.useForm<FormHoSo>()
  const [formMk] = Form.useForm<FormMatKhau>()

  if (loai !== 'noi_bo' || !hoSo) {
    return <Navigate to={DUONG_DANG_NHAP_NOI_BO} replace state={{ tu: vitri.pathname }} />
  }
  const veTrangChinh = duongSauDangNhap(hoSo.vaiTro)

  async function luuHoSo(gia_tri: FormHoSo) {
    if (dangGuiHoSo) return
    setDangGuiHoSo(true)
    setThongBaoHoSo(null)
    const kq = await goi(() =>
      api.PATCH('/api/v1/noi-bo/toi', {
        body: { ho_ten: gia_tri.ho_ten.trim(), so_dien_thoai: gia_tri.so_dien_thoai?.trim() || null },
      }),
    )
    setDangGuiHoSo(false)
    if (kq.ok) {
      usePhien.getState().capNhatHoSo(phienTuNhanVien(kq.data).hoSo)
      void message.success('Đã lưu hồ sơ')
      return
    }
    const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
    if (Object.keys(theoTruong).length > 0) {
      formHoSo.setFields(Object.entries(theoTruong).map(([name, loi]) => ({ name: name as keyof FormHoSo, errors: [loi] })))
    } else setThongBaoHoSo(thongDiepChung(kq.loi))
  }

  async function doiMatKhau(gia_tri: FormMatKhau) {
    if (dangGuiMk) return
    setDangGuiMk(true)
    setThongBaoMk(null)
    const kq = await goi(() =>
      api.POST('/api/v1/noi-bo/auth/doi-mat-khau', {
        body: { mat_khau_cu: gia_tri.mat_khau_cu, mat_khau_moi: gia_tri.mat_khau_moi },
      }),
    )
    setDangGuiMk(false)
    if (kq.ok) {
      // Mọi phiên cũ đã bị thu hồi; máy này nhận token mới ngay trong phản hồi.
      const batBuoc = phaiDoiMatKhau
      usePhien.getState().dangNhap({ accessToken: kq.data.access_token, loai: 'noi_bo', ...phienTuNhanVien(kq.data.nhan_vien) })
      formMk.resetFields()
      void message.success('Đã đổi mật khẩu. Các thiết bị khác đã bị đăng xuất.')
      if (batBuoc) dieuHuong(veTrangChinh, { replace: true })
      return
    }
    const loi = kq.loi
    if (loi?.ma_loi === 'MAT_KHAU_CU_SAI') {
      formMk.setFields([{ name: 'mat_khau_cu', errors: [loi.thong_diep] }])
    } else if (loi && (loi.ma_loi === 'TAI_KHOAN_BI_KHOA' || loi.ma_loi === 'QUA_GIOI_HAN')) {
      setThongBaoMk(thongDiepChoDoiLai(loi))
    } else if (loi && Object.keys(loiTheoTruong(loi)).length > 0) {
      formMk.setFields(Object.entries(loiTheoTruong(loi)).map(([name, thongDiep]) => ({ name: name as keyof FormMatKhau, errors: [thongDiep] })))
    } else setThongBaoMk(thongDiepChung(loi))
  }

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: 16 }}>
      {!phaiDoiMatKhau && (
        <Link to={veTrangChinh}>
          <ArrowLeftOutlined /> Quay lại
        </Link>
      )}
      <Typography.Title level={3}>Tài khoản của tôi</Typography.Title>
      {phaiDoiMatKhau && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="Bạn cần đổi mật khẩu trước khi tiếp tục"
          description="Đây là lần đăng nhập đầu hoặc mật khẩu của bạn vừa được đặt lại. Hãy chọn mật khẩu mới chỉ mình bạn biết."
        />
      )}

      {!phaiDoiMatKhau && (
        <Card title="Hồ sơ cá nhân" style={{ marginBottom: 16 }}>
          <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="Mã nhân viên">{hoSo.maNhanVien}</Descriptions.Item>
            <Descriptions.Item label="Email đăng nhập">{hoSo.email}</Descriptions.Item>
            <Descriptions.Item label="Vai trò">{tenVaiTro(hoSo.vaiTro)}</Descriptions.Item>
          </Descriptions>
          {thongBaoHoSo && <Alert type="error" showIcon title={thongBaoHoSo} style={{ marginBottom: 16 }} />}
          <Form
            key="ho-so"
            form={formHoSo}
            layout="vertical"
            requiredMark={false}
            onFinish={luuHoSo}
            initialValues={{ ho_ten: hoSo.hoTen, so_dien_thoai: hoSo.soDienThoai ?? '' }}
          >
            <Form.Item name="ho_ten" label="Họ và tên" rules={[{ required: true, whitespace: true, message: 'Vui lòng nhập họ và tên' }, { max: 150, message: 'Tối đa 150 ký tự' }]}>
              <Input autoComplete="name" />
            </Form.Item>
            <Form.Item
              name="so_dien_thoai"
              label="Số điện thoại (không bắt buộc)"
              rules={[{ validator: (_, v: string) => (!v?.trim() || chuanHoaSdt(v) ? Promise.resolve() : Promise.reject(new Error('Số điện thoại không hợp lệ (cần số di động Việt Nam 10 chữ số)'))) }]}
            >
              <Input inputMode="tel" autoComplete="tel" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={dangGuiHoSo}>
              Lưu hồ sơ
            </Button>
          </Form>
        </Card>
      )}

      <Card title="Đổi mật khẩu">
        {thongBaoMk && <Alert type="error" showIcon title={thongBaoMk} style={{ marginBottom: 16 }} />}
        <Form key="mat-khau" form={formMk} layout="vertical" requiredMark={false} onFinish={doiMatKhau}>
          <Form.Item name="mat_khau_cu" label="Mật khẩu hiện tại" rules={[{ required: true, message: 'Vui lòng nhập mật khẩu hiện tại' }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item
            name="mat_khau_moi"
            label="Mật khẩu mới"
            dependencies={['mat_khau_cu']}
            extra="Tối thiểu 8 ký tự, gồm cả chữ và số."
            rules={[
              { required: true, message: 'Vui lòng nhập mật khẩu mới' },
              ({ getFieldValue }) => ({
                validator: (_, v: string) => {
                  if (!v) return Promise.resolve()
                  if (!matKhauDuManh(v)) return Promise.reject(new Error('Mật khẩu cần tối thiểu 8 ký tự, gồm cả chữ và số'))
                  if (v === getFieldValue('mat_khau_cu')) return Promise.reject(new Error('Mật khẩu mới phải khác mật khẩu hiện tại'))
                  return Promise.resolve()
                },
              }),
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            name="nhap_lai_mat_khau"
            label="Nhập lại mật khẩu mới"
            dependencies={['mat_khau_moi']}
            rules={[
              { required: true, message: 'Vui lòng nhập lại mật khẩu' },
              ({ getFieldValue }) => ({
                validator: (_, v: string) => (!v || getFieldValue('mat_khau_moi') === v ? Promise.resolve() : Promise.reject(new Error('Mật khẩu nhập lại không khớp'))),
              }),
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={dangGuiMk}>
            Đổi mật khẩu
          </Button>
        </Form>
      </Card>
    </div>
  )
}

function tenVaiTro(ma?: string): string {
  return ma === 'ADMIN' ? 'Quản trị' : ma === 'PHARMACIST' ? 'Dược sĩ bán hàng' : ma === 'WAREHOUSE' ? 'Nhân viên kho' : (ma ?? '')
}
