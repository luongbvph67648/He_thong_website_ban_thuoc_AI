import { useQuery } from '@tanstack/react-query'
import { Alert, Space, Table, Tabs, Tag } from 'antd'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { NHAN_TRANG_THAI_LO } from './nhanKho'

type Lo = components['schemas']['LoCanhBao']
type Thap = components['schemas']['SanPhamThap']

/** KHO06: cảnh báo tồn thấp, lô cận hạn, lô hết hạn còn hàng (job HT01 chạy 00:05 hằng ngày). */
export default function TrangCanhBao() {
  const q = useQuery({
    queryKey: ['nhan-vien', 'canh-bao-kho'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/canh-bao-kho')
      if (error || !data) throw error ?? new Error('Không tải được cảnh báo')
      return data
    },
  })
  const d = q.data
  const bangLo = (ds: Lo[]) => (
    <Table<Lo>
      size="small"
      rowKey="lo_id"
      pagination={false}
      dataSource={ds}
      columns={[
        { title: 'Sản phẩm', key: 'sp', render: (_, l) => `${l.ten_san_pham} (${l.sku})` },
        { title: 'Số lô', dataIndex: 'so_lo', key: 'lo' },
        { title: 'HSD', key: 'hsd', render: (_, l) => dinhDangNgay(l.han_su_dung) },
        { title: 'Trạng thái', key: 'tt', render: (_, l) => <Tag color={NHAN_TRANG_THAI_LO[l.trang_thai].mau}>{NHAN_TRANG_THAI_LO[l.trang_thai].nhan}</Tag> },
        { title: 'Tồn', dataIndex: 'so_luong_ton', key: 'ton', align: 'right' },
        { title: 'Biệt trữ', dataIndex: 'so_luong_biet_tru', key: 'bt', align: 'right' },
      ]}
    />
  )
  const nhan = (ten: string, tong?: number) => `${ten} (${tong ?? 0})`
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      {q.isError && <Alert type="error" showIcon message="Không tải được cảnh báo kho" />}
      <Tabs
        items={[
          {
            key: 'thap',
            label: nhan('Tồn thấp', d?.ton_thap.tong),
            children: (
              <Table<Thap>
                size="small"
                rowKey="san_pham_id"
                pagination={false}
                loading={q.isLoading}
                dataSource={d?.ton_thap.du_lieu ?? []}
                columns={[
                  { title: 'Sản phẩm', key: 'sp', render: (_, s) => `${s.ten} (${s.sku})` },
                  { title: 'Khả dụng', dataIndex: 'ton_kha_dung', key: 'kd', align: 'right' },
                  { title: 'Mức tối thiểu', dataIndex: 'ton_toi_thieu', key: 'min', align: 'right' },
                ]}
              />
            ),
          },
          { key: 'can', label: nhan('Cận hạn', d?.can_han.tong), children: bangLo(d?.can_han.du_lieu ?? []) },
          { key: 'het', label: nhan('Hết hạn còn hàng', d?.het_han.tong), children: bangLo(d?.het_han.du_lieu ?? []) },
        ]}
      />
    </Space>
  )
}
