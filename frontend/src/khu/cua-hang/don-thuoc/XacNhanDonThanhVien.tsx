import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Spin } from 'antd'
import { api } from '../../../api/client'
import { goi } from '../../../api/goi'
import XacNhanDon from './XacNhanDon'

/** Thành viên xác nhận đơn do dược sĩ tạo từ đơn thuốc ngay trong trang chi tiết đơn (KTV07). */
export default function XacNhanDonThanhVien({ ma }: { ma: string }) {
  const qc = useQueryClient()
  const khoa = ['don-hang', ma, 'xac-nhan']
  const q = useQuery({
    queryKey: khoa,
    retry: false,
    queryFn: async () => (await api.GET('/api/v1/toi/don-hang/{ma_don}/xac-nhan', { params: { path: { ma_don: ma } } })).data ?? null,
  })
  if (q.isLoading) return <Spin />
  if (!q.data) return null
  const du = q.data
  return (
    <Alert
      type="warning"
      showIcon={false}
      title="Đơn từ đơn thuốc của bạn đang chờ xác nhận"
      description={
        <XacNhanDon
          duLieu={du}
          thanhVien
          lamMoi={() => {
            void qc.invalidateQueries({ queryKey: ['don-hang'] })
          }}
          xacNhan={(body) => goi(() => api.POST('/api/v1/toi/don-hang/{ma_don}/xac-nhan', { params: { path: { ma_don: ma } }, body }))}
          tuChoi={() => goi(() => api.POST('/api/v1/toi/don-hang/{ma_don}/tu-choi', { params: { path: { ma_don: ma } } }))}
          thanhToan={() =>
            goi(() =>
              api.POST('/api/v1/toi/don-hang/{ma_don}/thanh-toan', {
                params: { path: { ma_don: ma }, header: { 'Idempotency-Key': crypto.randomUUID() } },
              }),
            )
          }
        />
      }
    />
  )
}
