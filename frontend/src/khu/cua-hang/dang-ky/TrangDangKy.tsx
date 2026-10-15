import { Alert, Button, Card, Checkbox, Form, Input, Result, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import { laLoiApi, loiTheoTruong, type LoiApi } from '../../../api/loi'
import { chuanHoaSdt } from '../../../lib/dienThoai'
import { matKhauDuManh } from '../../../lib/matKhau'

const GIAY_CHO_GUI_LAI = 60

interface FormSdt {
  so_dien_thoai: string
}

interface FormThongTin {
  otp: string
  ho_ten: string
  email?: string
  mat_khau: string
  nhap_lai_mat_khau: string
  dong_y_chinh_sach: boolean
}

type KetQuaGoi<T> = { ok: true; data: T } | { ok: false; loi: LoiApi | null }

/** Gọi API và quy mọi kết quả (kể cả lỗi mạng) về một dạng; `loi = null` nghĩa là không nhận được phản hồi hợp lệ. */
async function goi<T>(thucHien: () => Promise<{ data?: T; error?: unknown }>): Promise<KetQuaGoi<T>> {
  try {
    const { data, error } = await thucHien()
    if (data !== undefined && !error) return { ok: true, data }
    return { ok: false, loi: laLoiApi(error) ? error : null }
  } catch {
    return { ok: false, loi: null }
  }
}

function thongDiepChung(loi: LoiApi | null): string {
  return loi ? loi.thong_diep : 'Không kết nối được máy chủ, vui lòng thử lại.'
}

function thongDiepChoDoiLai(loi: LoiApi): string {
  const giay = (loi.chi_tiet as { thu_lai_sau_giay?: number } | null)?.thu_lai_sau_giay
  return giay ? `${loi.thong_diep}. Hãy thử lại sau ${Math.ceil(giay / 60)} phút.` : loi.thong_diep
}

/** Đăng ký khách hàng 2 bước (KVL09): nhập số điện thoại để nhận OTP, rồi nhập mã cùng thông tin tài khoản. */
export default function TrangDangKy() {
  const [buoc, setBuoc] = useState<'sdt' | 'thong-tin' | 'xong'>('sdt')
  const [sdt, setSdt] = useState('')
  const [dangGui, setDangGui] = useState(false)
  const [thongBao, setThongBao] = useState<string | null>(null)
  const [giayCon, setGiayCon] = useState(0)
  const [formSdt] = Form.useForm<FormSdt>()
  const [formThongTin] = Form.useForm<FormThongTin>()

  const dangDem = giayCon > 0
  useEffect(() => {
    if (!dangDem) return
    const dong = setInterval(() => setGiayCon((g) => Math.max(0, g - 1)), 1000)
    return () => clearInterval(dong)
  }, [dangDem])

  async function guiOtp(so: string): Promise<boolean> {
    setDangGui(true)
    setThongBao(null)
    const kq = await goi(() => api.POST('/api/v1/auth/otp', { body: { so_dien_thoai: so, muc_dich: 'dang_ky' } }))
    setDangGui(false)
    if (kq.ok) {
      setGiayCon(GIAY_CHO_GUI_LAI)
      return true
    }
    if (kq.loi?.ma_loi === 'QUA_GIOI_HAN') setThongBao(thongDiepChoDoiLai(kq.loi))
    else {
      const loiTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      if (loiTruong.so_dien_thoai) formSdt.setFields([{ name: 'so_dien_thoai', errors: [loiTruong.so_dien_thoai] }])
      else setThongBao(thongDiepChung(kq.loi))
    }
    return false
  }

  async function submitSdt({ so_dien_thoai }: FormSdt) {
    const so = chuanHoaSdt(so_dien_thoai)
    if (!so || dangGui) return
    if (await guiOtp(so)) {
      setSdt(so)
      setBuoc('thong-tin')
    }
  }

  async function submitThongTin(gia_tri: FormThongTin) {
    if (dangGui) return
    setDangGui(true)
    setThongBao(null)
    const kq = await goi(() =>
      api.POST('/api/v1/auth/dang-ky', {
        body: {
          so_dien_thoai: sdt,
          otp: gia_tri.otp,
          mat_khau: gia_tri.mat_khau,
          ho_ten: gia_tri.ho_ten.trim(),
          email: gia_tri.email?.trim() || null,
          dong_y_chinh_sach: true,
        },
      }),
    )
    setDangGui(false)
    if (kq.ok) return setBuoc('xong')

    const loi = kq.loi
    if (loi?.ma_loi === 'OTP_SAI') {
      const conLai = (loi.chi_tiet as { so_lan_con_lai?: number } | null)?.so_lan_con_lai
      const noiDung = conLai && conLai > 0 ? `${loi.thong_diep}. Bạn còn ${conLai} lần thử.` : loi.thong_diep
      formThongTin.setFields([{ name: 'otp', errors: [noiDung] }])
    } else if (loi?.ma_loi === 'OTP_HET_HAN') {
      formThongTin.setFields([{ name: 'otp', errors: [loi.thong_diep] }])
    } else if (loi && Object.keys(loiTheoTruong(loi)).length > 0) {
      formThongTin.setFields(
        Object.entries(loiTheoTruong(loi)).map(([name, thongDiep]) => ({ name: name as keyof FormThongTin, errors: [thongDiep] })),
      )
    } else {
      setThongBao(thongDiepChung(loi))
    }
  }

  if (buoc === 'xong') {
    return (
      <Result
        status="success"
        title="Đăng ký thành công"
        subTitle="Tài khoản của bạn đã sẵn sàng. Hãy đăng nhập để bắt đầu mua sắm."
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
        Đăng ký tài khoản
      </Typography.Title>
      {thongBao && <Alert type="error" showIcon title={thongBao} style={{ marginBottom: 16 }} />}

      {/* `key` riêng cho mỗi Form: hai Form cùng vị trí nếu không có key sẽ bị React dùng lại một phiên bản và giữ instance `form` cũ. */}
      {buoc === 'sdt' ? (
        <Form key="sdt" form={formSdt} layout="vertical" onFinish={submitSdt} requiredMark={false}>
          <Form.Item
            name="so_dien_thoai"
            label="Số điện thoại"
            extra="Chúng tôi gửi mã xác thực qua tin nhắn SMS."
            rules={[
              { required: true, message: 'Vui lòng nhập số điện thoại' },
              { validator: (_, v: string) => (!v || chuanHoaSdt(v) ? Promise.resolve() : Promise.reject(new Error('Số điện thoại không hợp lệ (cần số di động Việt Nam 10 chữ số)'))) },
            ]}
          >
            <Input inputMode="tel" autoComplete="tel" placeholder="0912 345 678" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={dangGui}>
            Gửi mã xác thực
          </Button>
        </Form>
      ) : (
        <Form key="thong-tin" form={formThongTin} layout="vertical" onFinish={submitThongTin} requiredMark={false}>
          <Typography.Paragraph>
            Mã xác thực đã được gửi tới <strong>{sdt}</strong>.{' '}
            <Button type="link" style={{ padding: 0 }} onClick={() => setBuoc('sdt')}>
              Đổi số điện thoại
            </Button>
          </Typography.Paragraph>
          <Form.Item
            name="otp"
            label="Mã xác thực"
            rules={[{ pattern: /^\d{6}$/, message: 'Mã gồm 6 chữ số' }, { required: true, message: 'Vui lòng nhập mã xác thực' }]}
            extra={
              <Button type="link" style={{ padding: 0 }} disabled={giayCon > 0 || dangGui} onClick={() => void guiOtp(sdt)}>
                {giayCon > 0 ? `Gửi lại mã (${giayCon}s)` : 'Gửi lại mã'}
              </Button>
            }
          >
            <Input inputMode="numeric" autoComplete="one-time-code" maxLength={6} />
          </Form.Item>
          <Form.Item name="ho_ten" label="Họ và tên" rules={[{ required: true, whitespace: true, message: 'Vui lòng nhập họ và tên' }, { max: 150, message: 'Tối đa 150 ký tự' }]}>
            <Input autoComplete="name" />
          </Form.Item>
          <Form.Item name="email" label="Email (không bắt buộc)" normalize={(v: string) => v?.trim()} rules={[{ type: 'email', message: 'Email không hợp lệ' }]} extra="Dùng để nhận thông báo và lấy lại mật khẩu.">
            <Input autoComplete="email" />
          </Form.Item>
          <Form.Item
            name="mat_khau"
            label="Mật khẩu"
            rules={[
              { required: true, message: 'Vui lòng nhập mật khẩu' },
              { validator: (_, v: string) => (!v || matKhauDuManh(v) ? Promise.resolve() : Promise.reject(new Error('Mật khẩu cần tối thiểu 8 ký tự, gồm cả chữ và số'))) },
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            name="nhap_lai_mat_khau"
            label="Nhập lại mật khẩu"
            dependencies={['mat_khau']}
            rules={[
              { required: true, message: 'Vui lòng nhập lại mật khẩu' },
              ({ getFieldValue }) => ({
                validator: (_, v: string) => (!v || getFieldValue('mat_khau') === v ? Promise.resolve() : Promise.reject(new Error('Mật khẩu nhập lại không khớp'))),
              }),
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            name="dong_y_chinh_sach"
            valuePropName="checked"
            rules={[{ validator: (_, v: boolean) => (v ? Promise.resolve() : Promise.reject(new Error('Bạn cần đồng ý với chính sách để đăng ký'))) }]}
          >
            <Checkbox>Tôi đồng ý với chính sách của nhà thuốc</Checkbox>
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={dangGui}>
            Đăng ký
          </Button>
        </Form>
      )}
    </Card>
  )
}
