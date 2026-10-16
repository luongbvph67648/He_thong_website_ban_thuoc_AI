import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Descriptions, Drawer, Select, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'

type Tom = components['schemas']['DieuChinhTomTat']
type TrangThai = components['schemas']['TrangThaiDuyet']
const NHAN: Record<TrangThai, { nhan: string; mau: string }> = {
  cho_duyet: { nhan: 'Chờ duyệt', mau: 'gold' },
  da_duyet: { nhan: 'Đã duyệt', mau: 'green' },
  tu_choi: { nhan: 'Từ chối', mau: 'red' },
}

/** KHO08: danh sách và chi tiết phiếu điều chỉnh tồn. Phiếu lập từ kiểm kê ở màn Kiểm kê; Admin duyệt ở T3.4. */
export default function TrangDieuChinh() {
  const [trangThai, setTrangThai] = useState<TrangThai | undefined>()
  const [trang, setTrang] = useState(1)
  const [xem, setXem] = useState<number | null>(null)
  const ds = useQuery({
    queryKey: ['nhan-vien', 'dieu-chinh', trangThai, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/dieu-chinh', { params: { query: { trang_thai_duyet: trangThai, trang, kich_thuoc: 20 } } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
    placeholderData: (truoc) => truoc,
  })
  const ct = useQuery({
    queryKey: ['nhan-vien', 'dieu-chinh', 'ct', xem],
    enabled: xem !== null,
    queryFn: async () => (await api.GET('/api/v1/noi-bo/dieu-chinh/{phieu_id}', { params: { path: { phieu_id: xem as number } } })).data,
  })
  const cot: ColumnsType<Tom> = [
    { title: 'Mã phiếu', key: 'ma', render: (_, p) => <Button type="link" style={{ padding: 0 }} onClick={() => setXem(p.id)}>{p.ma_phieu}</Button> },
    { title: 'Từ kiểm kê', key: 'kk', render: (_, p) => p.ma_phieu_kiem_ke ?? 'Lập tay' },
    { title: 'Lý do', dataIndex: 'ly_do', key: 'ld', ellipsis: true },
    { title: 'Số dòng', dataIndex: 'so_dong', key: 'sd', align: 'right' },
    { title: 'Trạng thái', key: 'tt', render: (_, p) => <Tag color={NHAN[p.trang_thai_duyet].mau}>{NHAN[p.trang_thai_duyet].nhan}</Tag> },
    { title: 'Ngày lập', key: 'ngay', render: (_, p) => dinhDangNgay(p.created_at, 'ngayGio') },
  ]
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Select allowClear placeholder="Trạng thái" style={{ width: 180 }} value={trangThai} onChange={(v) => { setTrangThai(v); setTrang(1) }} options={(Object.keys(NHAN) as TrangThai[]).map((k) => ({ value: k, label: NHAN[k].nhan }))} />
      {ds.isError && <Alert type="error" showIcon message="Không tải được danh sách phiếu điều chỉnh" />}
      <Table<Tom> rowKey="id" columns={cot} dataSource={ds.data?.du_lieu ?? []} loading={ds.isLoading} pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }} />
      <Drawer title="Phiếu điều chỉnh tồn" open={xem !== null} onClose={() => setXem(null)} size="large" destroyOnHidden>
        {ct.data && (
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="Mã phiếu">{ct.data.ma_phieu}</Descriptions.Item>
              <Descriptions.Item label="Trạng thái">{NHAN[ct.data.trang_thai_duyet].nhan}</Descriptions.Item>
              <Descriptions.Item label="Người lập">{ct.data.nguoi_lap.ho_ten}</Descriptions.Item>
              <Descriptions.Item label="Người duyệt">{ct.data.nguoi_duyet?.ho_ten ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="Lý do" span={2}>{ct.data.ly_do}</Descriptions.Item>
              {ct.data.ly_do_tu_choi && <Descriptions.Item label="Lý do từ chối" span={2}>{ct.data.ly_do_tu_choi}</Descriptions.Item>}
            </Descriptions>
            <Table
              size="small"
              rowKey="lo_id"
              pagination={false}
              dataSource={ct.data.dong}
              columns={[
                { title: 'Sản phẩm', key: 'sp', render: (_, d) => `${d.san_pham.ten} (${d.san_pham.sku})` },
                { title: 'Số lô', dataIndex: 'so_lo', key: 'lo' },
                { title: 'Tồn hiện tại', dataIndex: 'so_luong_ton_hien_tai', key: 'ton', align: 'right' },
                { title: 'Thay đổi', key: 'td', align: 'right', render: (_, d) => (d.so_luong_thay_doi > 0 ? `+${d.so_luong_thay_doi}` : d.so_luong_thay_doi) },
              ]}
            />
          </Space>
        )}
      </Drawer>
    </Space>
  )
}
