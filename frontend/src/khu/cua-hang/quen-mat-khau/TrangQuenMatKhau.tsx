import { Alert, Button, Card, Form, Input, Radio, Result, Typography } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChoDoiLai, thongDiepChung, thongDiepOtpSai } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import { chuanHoaSdt } from '../../../lib/dienThoai'
import { matKhauDuManh } from '../../../lib/matKhau'
import { useDemNguoc } from '../../../lib/useDemNguoc'

const GIAY_CHO_GUI_LAI = 60

type Kenh = 'sms' | 'email'

interface FormYeuCau {
  so_dien_thoai: string
  kenh: Kenh
}

interface FormDatLai {
  otp: string
  mat_khau_moi: string
  nhap_lai_mat_khau: string
}

/**
 * Lấy lại mật khẩu (KVL10) 2 bước: nhập số điện thoại và chọn nhận mã qua SMS hoặc email, rồi nhập mã cùng mật khẩu
 * mới. Thông báo sau khi gửi không cho biết số có tài khoản hay không (chống dò tài khoản).
 */
export default function TrangQuenMatKhau() {
  const [buoc, setBuoc] = useState<'yeu-cau' | 'dat-lai' | 'xong'>('yeu-cau')
  const [sdt, setSdt] = useState('')
  const [kenh, setKenh] = useState<Kenh>('sms')
  const [dangGui, setDangGui] = useState(false)
  const [thongBao, setThongBao] = useState<string | null>(null)
  const [giayCon, batDauDem] = useDemNguoc()
  const [formYeuCau] = Form.useForm<FormYeuCau>()
  const [formDatLai] = Form.useForm<FormDatLai>()

  async function guiOtp(so: string, kenhNhan: Kenh): Promise<boolean> {
    setDangGui(true)
    setThongBao(null)
    const kq = await goi(() =>
      api.POST('/api/v1/auth/otp', { body: { so_dien_thoai: so, muc_dich: 'quen_mat_khau', kenh: kenhNhan } }),
    )
    setDangGui(false)
    if (kq.ok) {
      batDauDem(GIAY_CHO_GUI_LAI)
      return true
    }
    if (kq.loi?.ma_loi === 'QUA_GIOI_HAN') setThongBao(thongDiepChoDoiLai(kq.loi))
    else {
      const loiTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      if (loiTruong.so_dien_thoai) formYeuCau.setFields([{ name: 'so_dien_thoai', errors: [loiTruong.so_dien_thoai] }])
      else setThongBao(thongDiepChung(kq.loi))
    }
    return false
  }

  async function submitYeuCau(gia_tri: FormYeuCau) {
    const so = chuanHoaSdt(gia_tri.so_dien_thoai)
    if (!so || dangGui) return
    if (await guiOtp(so, gia_tri.kenh)) {
      setSdt(so)
      setKenh(gia_tri.kenh)
      setBuoc('dat-lai')
    }
  }

  async function submitDatLai(gia_tri: FormDatLai) {
    if (dangGui) return
    setDangGui(true)
    setThongBao(null)
    const kq = await goi(() =>
      api.POST('/api/v1/auth/dat-lai-mat-khau', {
        body: { so_dien_thoai: sdt, otp: gia_tri.otp, mat_khau_moi: gia_tri.mat_khau_moi },
      }),
    )
    setDangGui(false)
    if (kq.ok) return setBuoc('xong')

    const loi = kq.loi
    if (loi?.ma_loi === 'OTP_SAI') formDatLai.setFields([{ name: 'otp', errors: [thongDiepOtpSai(loi)] }])
    else if (loi?.ma_loi === 'OTP_HET_HAN') formDatLai.setFields([{ name: 'otp', errors: [loi.thong_diep] }])
    else if (loi && Object.keys(loiTheoTruong(loi)).length > 0) {
      formDatLai.setFields(
        Object.entries(loiTheoTruong(loi)).map(([name, thongDiep]) => ({ name: name as keyof FormDatLai, errors: [thongDiep] })),
      )
    } else setThongBao(thongDiepChung(loi))
  }

  if (buoc === 'xong') {
    return (
      <Result
        status="success"
        title="Đã đặt lại mật khẩu"
        subTitle="Mọi thiết bị đang đăng nhập đã bị đăng xuất. Hãy đăng nhập bằng mật khẩu mới."
        extra={
          <Link to="/dang-nhap">
            <Button type="primary">Đăng nhập</Button>
          </Link>
        }
      />
    )
  }

  return (
    <Card style={{ maxWidth: 480, margin: '16px auto' }}>
      <Typography.Title level={2} style={{ marginTop: 0 }}>
        Quên mật khẩu
      </Typography.Title>
      {thongBao && <Alert type="error" showIcon title={thongBao} style={{ marginBottom: 16 }} />}

      {/* `key` riêng cho mỗi Form: hai Form cùng vị trí nếu không có key sẽ bị React dùng lại một phiên bản. */}
      {buoc === 'yeu-cau' ? (
        <Form key="yeu-cau" form={formYeuCau} layout="vertical" onFinish={submitYeuCau} requiredMark={false} initialValues={{ kenh: 'sms' }}>
          <Form.Item
            name="so_dien_thoai"
            label="Số điện thoại đã đăng ký"
            rules={[
              { required: true, message: 'Vui lòng nhập số điện thoại' },
              { validator: (_, v: string) => (!v || chuanHoaSdt(v) ? Promise.resolve() : Promise.reject(new Error('Số điện thoại không hợp lệ (cần số di động Việt Nam 10 chữ số)'))) },
            ]}
          >
            <Input inputMode="tel" autoComplete="tel" placeholder="0912 345 678" />
          </Form.Item>
          <Form.Item name="kenh" label="Nhận mã xác thực qua" extra="Chọn email nếu tài khoản đã có email; chưa có thì mã được gửi qua SMS.">
            <Radio.Group
              options={[
                { value: 'sms', label: 'Tin nhắn SMS' },
                { value: 'email', label: 'Email đã đăng ký' },
              ]}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={dangGui}>
            Gửi mã xác thực
          </Button>
        </Form>
      ) : (
        <Form key="dat-lai" form={formDatLai} layout="vertical" onFinish={submitDatLai} requiredMark={false}>
          <Typography.Paragraph>
            Nếu số <strong>{sdt}</strong> đã đăng ký, mã xác thực đã được gửi qua {kenh === 'email' ? 'email' : 'tin nhắn SMS'}.{' '}
            <Button type="link" style={{ padding: 0 }} onClick={() => setBuoc('yeu-cau')}>
              Đổi số điện thoại
            </Button>
          </Typography.Paragraph>
          <Form.Item
            name="otp"
            label="Mã xác thực"
            rules={[{ pattern: /^\d{6}$/, message: 'Mã gồm 6 chữ số' }, { required: true, message: 'Vui lòng nhập mã xác thực' }]}
            extra={
              <Button type="link" style={{ padding: 0 }} disabled={giayCon > 0 || dangGui} onClick={() => void guiOtp(sdt, kenh)}>
                {giayCon > 0 ? `Gửi lại mã (${giayCon}s)` : 'Gửi lại mã'}
              </Button>
            }
          >
            <Input inputMode="numeric" autoComplete="one-time-code" maxLength={6} />
          </Form.Item>
          <Form.Item
            name="mat_khau_moi"
            label="Mật khẩu mới"
            rules={[
              { required: true, message: 'Vui lòng nhập mật khẩu mới' },
              { validator: (_, v: string) => (!v || matKhauDuManh(v) ? Promise.resolve() : Promise.reject(new Error('Mật khẩu cần tối thiểu 8 ký tự, gồm cả chữ và số'))) },
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
          <Button type="primary" htmlType="submit" block loading={dangGui}>
            Đặt lại mật khẩu
          </Button>
        </Form>
      )}
      <div style={{ marginTop: 16 }}>
        <Link to="/dang-nhap">Quay lại đăng nhập</Link>
      </div>
    </Card>
  )
}
