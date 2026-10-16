import { InboxOutlined } from '@ant-design/icons'
import { Alert, Button, Form, Input, Result, Space, Typography, Upload } from 'antd'
import type { UploadFile } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChoDoiLai, thongDiepChung, thongDiepOtpSai } from '../../../api/goi'
import { chuanHoaSdt } from '../../../lib/dienThoai'
import { useDemNguoc } from '../../../lib/useDemNguoc'
import { usePhien } from '../../../stores/phien'

const KIEU = ['image/jpeg', 'image/png', 'image/webp']
const TOI_DA_ANH = 5
const TOI_DA_BYTE = 5 * 1024 * 1024

interface FormGui {
  ho_ten: string
  so_dien_thoai: string
  ghi_chu?: string
  otp?: string
  anh: UploadFile[]
}

/** KVL08, KTV07: gửi ảnh đơn thuốc nhờ dược sĩ tư vấn. Khách vãng lai xác thực số điện thoại bằng OTP. */
export default function TrangGuiDonThuoc() {
  const khach = usePhien((s) => s.loai === 'khach')
  const hoTen = usePhien((s) => s.hoSo?.hoTen)
  const [form] = Form.useForm<FormGui>()
  const [dangGui, setDangGui] = useState(false)
  const [loi, setLoi] = useState<string | null>(null)
  const [ma, setMa] = useState<string | null>(null)
  const [giayCon, batDauDem] = useDemNguoc()

  async function guiOtp() {
    const sdt = chuanHoaSdt(form.getFieldValue('so_dien_thoai') ?? '')
    if (!sdt) return form.setFields([{ name: 'so_dien_thoai', errors: ['Số điện thoại không hợp lệ'] }])
    setLoi(null)
    const kq = await goi(() => api.POST('/api/v1/auth/otp', { body: { so_dien_thoai: sdt, muc_dich: 'don_thuoc_khach', kenh: 'sms' } }))
    if (kq.ok) batDauDem(60)
    else setLoi(kq.loi?.ma_loi === 'QUA_GIOI_HAN' ? thongDiepChoDoiLai(kq.loi) : thongDiepChung(kq.loi))
  }

  async function gui(v: FormGui) {
    const files = v.anh.map((f) => f.originFileObj).filter((f): f is NonNullable<typeof f> => !!f)
    setDangGui(true)
    setLoi(null)
    const kq = await goi(() =>
      api.POST('/api/v1/don-thuoc', {
        body: { anh: [] },
        bodySerializer: () => {
          const fd = new FormData()
          files.forEach((f) => fd.append('anh', f))
          if (v.ho_ten) fd.append('ho_ten', v.ho_ten)
          const sdt = chuanHoaSdt(v.so_dien_thoai ?? '')
          if (sdt) fd.append('so_dien_thoai', sdt)
          if (v.ghi_chu) fd.append('ghi_chu', v.ghi_chu)
          if (!khach && v.otp) fd.append('otp', v.otp)
          return fd
        },
      }),
    )
    setDangGui(false)
    if (kq.ok) setMa(kq.data.ma_yeu_cau)
    else setLoi(kq.loi?.ma_loi === 'OTP_SAI' ? thongDiepOtpSai(kq.loi) : thongDiepChung(kq.loi))
  }

  if (ma)
    return (
      <Result
        status="success"
        title="Đã gửi đơn thuốc"
        subTitle={`Mã yêu cầu ${ma}. Dược sĩ sẽ xem đơn và liên hệ bạn qua số điện thoại đã cung cấp.`}
        extra={khach ? <Link to="/tai-khoan/don-thuoc">Xem đơn thuốc của tôi</Link> : <Link to="/">Về trang chủ</Link>}
      />
    )

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%', maxWidth: 640 }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Gửi đơn thuốc cho dược sĩ</Typography.Title>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Chụp rõ đơn thuốc của bác sĩ. Dược sĩ kiểm tra rồi tư vấn và tạo đơn hàng cho bạn xác nhận. Thuốc kê đơn không bán trực tiếp qua giỏ hàng.
      </Typography.Paragraph>
      {loi && <Alert type="error" showIcon title={loi} />}
      <Form form={form} layout="vertical" onFinish={(v) => void gui(v)} initialValues={{ ho_ten: hoTen, anh: [] }}>
        <Form.Item name="ho_ten" label="Họ tên người bệnh" rules={[{ required: true, message: 'Nhập họ tên' }]}>
          <Input maxLength={150} />
        </Form.Item>
        <Form.Item
          name="so_dien_thoai"
          label="Số điện thoại liên hệ"
          rules={[
            { required: true, message: 'Nhập số điện thoại' },
            { validator: (_, v: string) => (!v || chuanHoaSdt(v) ? Promise.resolve() : Promise.reject(new Error('Số điện thoại không hợp lệ'))) },
          ]}
        >
          <Input inputMode="tel" />
        </Form.Item>
        {!khach && (
          <Form.Item label="Mã xác thực (OTP)" required>
            <Space.Compact style={{ width: '100%' }}>
              <Form.Item name="otp" noStyle rules={[{ required: true, message: 'Nhập mã OTP' }]}>
                <Input maxLength={6} inputMode="numeric" placeholder="6 chữ số" />
              </Form.Item>
              <Button onClick={() => void guiOtp()} disabled={giayCon > 0}>
                {giayCon > 0 ? `Gửi lại sau ${giayCon}s` : 'Gửi mã'}
              </Button>
            </Space.Compact>
          </Form.Item>
        )}
        <Form.Item
          name="anh"
          label="Ảnh đơn thuốc"
          valuePropName="fileList"
          getValueFromEvent={(e: { fileList: UploadFile[] }) => e.fileList}
          rules={[{ validator: (_, v: UploadFile[]) => (v?.length ? Promise.resolve() : Promise.reject(new Error('Chọn ít nhất một ảnh'))) }]}
          extra={`JPEG, PNG hoặc WebP, tối đa 5 MB mỗi ảnh, tối đa ${TOI_DA_ANH} ảnh.`}
        >
          <Upload.Dragger
            multiple
            listType="picture"
            accept={KIEU.join(',')}
            maxCount={TOI_DA_ANH}
            beforeUpload={(f) => {
              if (!KIEU.includes(f.type)) setLoi(`${f.name}: chỉ nhận ảnh JPEG, PNG hoặc WebP`)
              else if (f.size > TOI_DA_BYTE) setLoi(`${f.name}: ảnh quá 5 MB`)
              else return false
              return Upload.LIST_IGNORE
            }}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p>Bấm hoặc kéo ảnh đơn thuốc vào đây</p>
          </Upload.Dragger>
        </Form.Item>
        <Form.Item name="ghi_chu" label="Ghi chú cho dược sĩ">
          <Input.TextArea rows={3} maxLength={1000} showCount />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={dangGui}>Gửi đơn thuốc</Button>
      </Form>
    </Space>
  )
}
