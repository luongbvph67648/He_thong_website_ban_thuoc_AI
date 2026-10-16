import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Result, Spin, Typography } from 'antd'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi } from '../../../api/goi'
import { khoaTokenDon } from './donThuoc'
import XacNhanDon from './XacNhanDon'

/** KTV07: khách vãng lai xác nhận đơn từ đơn thuốc qua link mã truy cập (không cần đăng nhập). */
export default function TrangXacNhanDon() {
  const { token = '' } = useParams()
  const qc = useQueryClient()
  const khoa = ['xac-nhan-don', token]
  const q = useQuery({
    queryKey: khoa,
    retry: false,
    queryFn: async () => (await api.GET('/api/v1/xac-nhan-don/{token}', { params: { path: { token } } })).data ?? null,
  })
  if (q.isLoading) return <Spin />
  const du = q.data
  if (!du)
    return (
      <Result
        status="404"
        title="Liên kết không hợp lệ"
        subTitle="Liên kết đã hết hiệu lực hoặc bị sai. Vui lòng liên hệ nhà thuốc."
        extra={<Link to="/"><Button type="primary">Về trang chủ</Button></Link>}
      />
    )
  return (
    <>
      <Typography.Title level={2}>Xác nhận đơn hàng</Typography.Title>
      <XacNhanDon
        duLieu={du}
        thanhVien={false}
        lamMoi={() => void qc.invalidateQueries({ queryKey: khoa })}
        xacNhan={(body) => goi(() => api.POST('/api/v1/xac-nhan-don/{token}/xac-nhan', { params: { path: { token } }, body }))}
        tuChoi={() => goi(() => api.POST('/api/v1/xac-nhan-don/{token}/tu-choi', { params: { path: { token } } }))}
        thanhToan={() => {
          sessionStorage.setItem(khoaTokenDon(du.don.ma_don), token)
          return goi(() =>
            api.POST('/api/v1/xac-nhan-don/{token}/thanh-toan', {
              params: { path: { token }, header: { 'Idempotency-Key': crypto.randomUUID() } },
            }),
          )
        }}
      />
    </>
  )
}
