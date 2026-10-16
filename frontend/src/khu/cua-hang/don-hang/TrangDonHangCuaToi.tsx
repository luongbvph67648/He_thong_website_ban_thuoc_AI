import { useQuery } from '@tanstack/react-query'
import { Alert, Select, Space, Spin, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { TRANG_THAI, nhanTrangThai } from '../../../lib/trangThai'
import { usePhien } from '../../../stores/phien'
import MuaLaiNut from './MuaLaiNut'

type Don = components['schemas']['DonTomTat']
type TrangThai = components['schemas']['TrangThaiDon']

/** KTV06: đơn hàng của tôi (danh sách, lọc theo trạng thái); chi tiết và nút hủy ở trang con. */
export default function TrangDonHangCuaToi() {
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const khach = usePhien((s) => s.loai === 'khach')
  const [trangThai, setTrangThai] = useState<TrangThai | undefined>()
  const [trang, setTrang] = useState(1)
  const ds = useQuery({
    queryKey: ['don-hang', 'ds', trangThai, trang],
    enabled: khach,
    placeholderData: (truoc) => truoc,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/toi/don-hang', { params: { query: { trang_thai: trangThai, trang, kich_thuoc: 10 } } })
      if (error || !data) throw error ?? new Error('Không tải được đơn hàng')
      return data
    },
  })
  if (!daKhoiPhuc) return <Spin />
  if (!khach) return <Navigate to="/dang-nhap?tiep=/tai-khoan/don-hang" replace />
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Đơn hàng của tôi</Typography.Title>
      <Select<TrangThai>
        allowClear
        placeholder="Lọc theo trạng thái"
        style={{ width: 240 }}
        value={trangThai}
        onChange={(v) => { setTrangThai(v); setTrang(1) }}
        options={(Object.keys(TRANG_THAI.don_hang) as TrangThai[]).map((k) => ({ value: k, label: TRANG_THAI.don_hang[k].nhan }))}
      />
      {ds.isError && <Alert type="error" showIcon message="Không tải được danh sách đơn hàng" />}
      <Table<Don>
        rowKey="ma_don"
        loading={ds.isLoading}
        dataSource={ds.data?.du_lieu ?? []}
        pagination={{ current: trang, pageSize: 10, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }}
        columns={[
          { title: 'Mã đơn', key: 'ma', render: (_, d) => <Link to={`/tai-khoan/don-hang/${d.ma_don}`}>{d.ma_don}</Link> },
          { title: 'Ngày đặt', key: 'ngay', render: (_, d) => dinhDangNgay(d.created_at, 'ngayGio') },
          { title: 'Số sản phẩm', dataIndex: 'so_san_pham', key: 'sl', align: 'right' },
          { title: 'Tổng tiền', key: 'tien', align: 'right', render: (_, d) => dinhDangTien(d.tong_tien) },
          {
            title: 'Trạng thái',
            key: 'tt',
            render: (_, d) => {
              const n = nhanTrangThai('don_hang', d.trang_thai)
              return <Tag color={n.mau}>{n.nhan}</Tag>
            },
          },
          { title: '', key: 'mua-lai', render: (_, d) => <MuaLaiNut maDon={d.ma_don} /> },
        ]}
      />
    </Space>
  )
}
