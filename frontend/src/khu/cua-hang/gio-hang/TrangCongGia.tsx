import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Result, Spin } from 'antd'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import GiaMomo from './cong-gia/GiaMomo'
import GiaVnpay from './cong-gia/GiaVnpay'

/**
 * Cổng thanh toán GIẢ (spec 08 mục 4), chỉ khi `THANH_TOAN_CHE_DO=gia`: dựng giao diện mô phỏng VNPay hoặc MoMo (theo cổng
 * khách đã chọn khi đặt hàng) từ thông tin giao dịch của máy chủ. Kết quả gửi bằng IPN giả như cổng thật báo cho máy chủ,
 * rồi khách về trang kết quả đọc trạng thái từ máy chủ. Không có tiền thật.
 */
export default function TrangCongGia() {
  const [tham] = useSearchParams()
  const giaoDich = tham.get('giao_dich') ?? ''
  const q = useQuery({
    queryKey: ['cong-gia', giaoDich],
    enabled: giaoDich !== '',
    retry: false,
    staleTime: Infinity,
    queryFn: async () => (await api.GET('/api/v1/webhook/gia-giao-dich', { params: { query: { giao_dich: giaoDich } } })).data ?? null,
  })
  if (giaoDich === '') return <Alert type="error" showIcon message="Thiếu mã giao dịch" />
  if (q.isLoading) return <Spin />
  const gd = q.data
  if (!gd) return <Result status="404" title="Không tìm thấy giao dịch" extra={<Link to="/"><Button type="primary">Về trang chủ</Button></Link>} />
  if (gd.trang_thai !== 'khoi_tao') {
    return (
      <Result
        status="info"
        title="Giao dịch này đã được xử lý"
        extra={<Link to={`/thanh-toan/ket-qua?ma=${encodeURIComponent(gd.ma_don)}`}><Button type="primary">Xem đơn hàng</Button></Link>}
      />
    )
  }
  return gd.cong === 'momo' ? <GiaMomo gd={gd} /> : <GiaVnpay gd={gd} />
}
