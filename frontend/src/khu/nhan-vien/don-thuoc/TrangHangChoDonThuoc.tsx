import { useMutation, useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Space, Table, Tag, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'

type Hang = components['schemas']['HangChoRa']

/** DS04: hàng chờ yêu cầu đơn thuốc. Nhận xử lý = khóa yêu cầu cho mình; quá thời gian cấu hình hệ thống tự nhả (HT08). */
export default function TrangHangChoDonThuoc() {
  const { message } = App.useApp()
  const dieuHuong = useNavigate()
  const ds = useQuery({
    queryKey: ['noi-bo', 'don-thuoc'],
    refetchInterval: 30_000,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/don-thuoc')
      if (error || !data) throw error ?? new Error('Không tải được hàng chờ')
      return data
    },
  })
  const nhan = useMutation({
    mutationFn: async (id: number) => {
      const r = await goi(() => api.POST('/api/v1/noi-bo/don-thuoc/{yc_id}/nhan', { params: { path: { yc_id: id } } }))
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
      return id
    },
    onSuccess: (id) => dieuHuong(`/nhan-vien/don-thuoc/${id}`),
    onError: (e: Error) => {
      void message.error(e.message)
      void ds.refetch()
    },
  })
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Yêu cầu đơn thuốc</Typography.Title>
      {ds.isError && <Alert type="error" showIcon title="Không tải được hàng chờ" />}
      <Table<Hang>
        rowKey="id"
        loading={ds.isLoading}
        dataSource={ds.data ?? []}
        pagination={false}
        locale={{ emptyText: 'Không có yêu cầu nào đang chờ' }}
        columns={[
          { title: 'Mã', dataIndex: 'ma_yeu_cau' },
          { title: 'Người bệnh', dataIndex: 'ho_ten' },
          { title: 'SĐT', dataIndex: 'so_dien_thoai' },
          { title: 'Khách', dataIndex: 'la_thanh_vien', render: (v: boolean) => (v ? <Tag color="blue">Thành viên</Tag> : <Tag>Vãng lai</Tag>) },
          { title: 'Ảnh', dataIndex: 'so_anh', align: 'right' },
          { title: 'Gửi lúc', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          { title: 'Trạng thái', dataIndex: 'trang_thai', render: (t: Hang['trang_thai']) => (t === 'cho_duyet' ? <Tag color="gold">Chờ duyệt</Tag> : <Tag color="green">Tôi đang xử lý</Tag>) },
          {
            title: '',
            render: (_, r) => (
              <Button type="primary" size="small" loading={nhan.isPending && nhan.variables === r.id} onClick={() => nhan.mutate(r.id)}>
                {r.khoa_boi_toi ? 'Tiếp tục' : 'Nhận xử lý'}
              </Button>
            ),
          },
        ]}
      />
    </Space>
  )
}
