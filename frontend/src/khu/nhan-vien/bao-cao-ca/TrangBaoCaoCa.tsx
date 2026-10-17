import { useQuery } from '@tanstack/react-query'
import { Alert, DatePicker, Descriptions, Space, Typography } from 'antd'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import { api } from '../../../api/client'
import dayjs from '../../../lib/dayjs'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'

type Khoang = [Dayjs, Dayjs]

/** DS14: báo cáo bán hàng của ca cho chính dược sĩ (doanh thu, đơn thuốc đã duyệt, tiền thu tại quầy). Không có giá vốn. */
export default function TrangBaoCaoCa() {
  const [khoang, setKhoang] = useState<Khoang>(() => [dayjs().startOf('day').hour(8), dayjs()])
  const q = useQuery({
    queryKey: ['noi-bo', 'bao-cao', 'ca', khoang[0].toISOString(), khoang[1].toISOString()],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/bao-cao/ca', { params: { query: { tu: khoang[0].toISOString(), den: khoang[1].toISOString() } } })
      if (error || !data) throw error ?? new Error('Không tải được báo cáo ca')
      return data
    },
  })
  const d = q.data
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Báo cáo ca</Typography.Title>
      <DatePicker.RangePicker showTime={{ format: 'HH:mm' }} allowClear={false} value={khoang} format="DD/MM/YYYY HH:mm" onChange={(v) => v?.[0] && v[1] && setKhoang([v[0], v[1]])} />
      {q.isError && <Alert type="error" showIcon title="Không tải được báo cáo ca (tối đa 31 ngày, đầu ca phải trước cuối ca)" />}
      {d && (
        <Descriptions bordered size="small" column={1} title={`Từ ${dinhDangNgay(d.tu, 'ngayGio')} đến ${dinhDangNgay(d.den, 'ngayGio')}`}>
          <Descriptions.Item label="Số đơn do tôi xử lý">{d.so_don}</Descriptions.Item>
          <Descriptions.Item label="Doanh thu các đơn đó">{dinhDangTien(d.doanh_thu)}</Descriptions.Item>
          <Descriptions.Item label="Đơn thuốc đã duyệt">{d.so_don_thuoc_da_duyet}</Descriptions.Item>
          <Descriptions.Item label="Tiền mặt thu tại quầy">{dinhDangTien(d.tien_mat_thu_tai_quay)} ({d.so_giao_dich_tien_mat} giao dịch)</Descriptions.Item>
          <Descriptions.Item label="Chuyển khoản thu tại quầy">{dinhDangTien(d.chuyen_khoan_thu_tai_quay)}</Descriptions.Item>
        </Descriptions>
      )}
      <Typography.Text type="secondary">Đối chiếu tiền mặt cuối ca với số trong két. Báo cáo này không có giá vốn hay lợi nhuận.</Typography.Text>
    </Space>
  )
}
