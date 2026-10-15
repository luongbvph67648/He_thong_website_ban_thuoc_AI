import { useQuery } from '@tanstack/react-query'
import { Alert, Typography } from 'antd'
import { api } from '../../api/client'

/** Hiện tình trạng backend qua client có kiểu, để thấy ngay toàn tuyến (proxy, client, TanStack Query) hoạt động. */
function TrangThaiHeThong() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['suc-khoe'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/health')
      if (error || !data) throw new Error('Backend không phản hồi')
      return data
    },
  })
  if (isPending) return <Alert type="info" title="Đang kiểm tra hệ thống…" />
  if (isError) return <Alert type="error" showIcon title="Không kết nối được backend" />
  return <Alert type="success" showIcon title={`Backend: ${data.trang_thai} · CSDL: ${data.db}`} />
}

export default function TrangChu() {
  return (
    <>
      <Typography.Title level={1}>Nhà thuốc trực tuyến</Typography.Title>
      <Typography.Paragraph>Trang chủ cửa hàng (KVL01) đang được xây dựng.</Typography.Paragraph>
      <TrangThaiHeThong />
    </>
  )
}
