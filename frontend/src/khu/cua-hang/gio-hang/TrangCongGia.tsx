import { Alert, App, Button, Card, Space, Typography } from 'antd'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { maDonTuGiaoDich } from './thanhToanOnline'

/**
 * Cổng thanh toán GIẢ (spec 08 mục 4), chỉ để dev/demo: bấm Thành công hoặc Thất bại thì gửi IPN giả lên backend
 * (route chỉ tồn tại khi `THANH_TOAN_CHE_DO=gia`), rồi quay về trang kết quả đọc trạng thái từ máy chủ.
 */
export default function TrangCongGia() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [tham] = useSearchParams()
  const giaoDich = tham.get('giao_dich') ?? ''
  const [dangGui, datDangGui] = useState<boolean | null>(null)

  async function bam(thanhCong: boolean) {
    datDangGui(thanhCong)
    const r = await goi(() => api.POST('/api/v1/webhook/gia-ipn', { body: { giao_dich: giaoDich, thanh_cong: thanhCong } }))
    datDangGui(null)
    if (!r.ok) {
      void message.error(thongDiepChung(r.loi))
      return
    }
    navigate(`/thanh-toan/ket-qua?ma=${encodeURIComponent(maDonTuGiaoDich(giaoDich))}`)
  }

  return (
    <Card style={{ maxWidth: 480 }} title="Cổng thanh toán giả">
      <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
        <Alert type="warning" showIcon message="Chỉ dùng khi phát triển, không có tiền thật." />
        {giaoDich === '' ? (
          <Alert type="error" showIcon message="Thiếu mã giao dịch" />
        ) : (
          <>
            <Typography.Text>Mã giao dịch: <b>{giaoDich}</b></Typography.Text>
            <Space>
              <Button type="primary" loading={dangGui === true} disabled={dangGui !== null} onClick={() => bam(true)}>Thành công</Button>
              <Button danger loading={dangGui === false} disabled={dangGui !== null} onClick={() => bam(false)}>Thất bại</Button>
            </Space>
          </>
        )}
      </Space>
    </Card>
  )
}
