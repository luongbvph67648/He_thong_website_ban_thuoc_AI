import { useQuery } from '@tanstack/react-query'
import { Alert, Table, Tabs, Tag } from 'antd'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { nhanTrangThai } from '../../../lib/trangThai'

type Don = components['schemas']['DonNoiBoTomTat']
type TrangThai = components['schemas']['TrangThaiDon']

const HANG_DOI: readonly { khoa: TrangThai; nhan: string }[] = [
  { khoa: 'da_xac_nhan', nhan: 'Chờ soạn' },
  { khoa: 'dang_soan_hang', nhan: 'Đang soạn' },
  { khoa: 'cho_lay_hang', nhan: 'Chờ lấy hàng' },
]

/** KHO03, KHO04: hàng đợi của kho theo trạng thái; bấm mã đơn để mở phiếu soạn hàng. */
export default function TrangSoanHang() {
  const goc = useLocation().pathname.replace(/\/+$/, '')
  const [trangThai, setTrangThai] = useState<TrangThai>('da_xac_nhan')
  const [trang, setTrang] = useState(1)
  const ds = useQuery({
    queryKey: ['nhan-vien', 'soan-hang', trangThai, trang],
    placeholderData: (truoc) => truoc,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/don-hang', { params: { query: { trang_thai: trangThai, trang, kich_thuoc: 20 } } })
      if (error || !data) throw error ?? new Error('Không tải được hàng đợi')
      return data
    },
  })
  return (
    <>
      <Tabs
        activeKey={trangThai}
        onChange={(k) => { setTrangThai(k as TrangThai); setTrang(1) }}
        items={HANG_DOI.map((h) => ({ key: h.khoa, label: h.nhan }))}
      />
      {ds.isError && <Alert type="error" showIcon message="Không tải được hàng đợi soạn hàng" style={{ marginBottom: 12 }} />}
      <Table<Don>
        rowKey="id"
        loading={ds.isLoading}
        dataSource={ds.data?.du_lieu ?? []}
        pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }}
        columns={[
          { title: 'Mã đơn', key: 'ma', render: (_, d) => <Link to={`${goc}/${d.id}`}>{d.ma_don}</Link> },
          { title: 'Ngày đặt', key: 'ngay', render: (_, d) => dinhDangNgay(d.created_at, 'ngayGio') },
          { title: 'Người nhận', key: 'nguoi', render: (_, d) => [d.ten_nguoi_nhan, d.sdt_nguoi_nhan].filter(Boolean).join(' · ') || '—' },
          { title: 'Số sản phẩm', dataIndex: 'so_san_pham', key: 'sl', align: 'right' },
          { title: 'Trạng thái', key: 'tt', render: (_, d) => { const n = nhanTrangThai('don_hang', d.trang_thai); return <Tag color={n.mau}>{n.nhan}</Tag> } },
        ]}
      />
    </>
  )
}
