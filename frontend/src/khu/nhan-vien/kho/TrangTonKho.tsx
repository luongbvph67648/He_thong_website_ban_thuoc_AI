import { useQuery } from '@tanstack/react-query'
import { Alert, Input, Space, Switch, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { NHAN_TRANG_THAI_LO } from './nhanKho'

type Ton = components['schemas']['TonSanPham']
type Lo = components['schemas']['TonLo']

function BangLo({ id }: { id: number }) {
  const q = useQuery({
    queryKey: ['nhan-vien', 'ton-kho', 'lo', id],
    queryFn: async () => (await api.GET('/api/v1/noi-bo/ton-kho/{san_pham_id}/lo', { params: { path: { san_pham_id: id } } })).data ?? [],
  })
  const coChiTiet = (q.data ?? []).some((l) => l.so_luong_ton !== null)
  const cot: ColumnsType<Lo> = [
    { title: 'Số lô', dataIndex: 'so_lo', key: 'lo' },
    { title: 'HSD', key: 'hsd', render: (_, l) => dinhDangNgay(l.han_su_dung) },
    { title: 'Trạng thái', key: 'tt', render: (_, l) => <Tag color={NHAN_TRANG_THAI_LO[l.trang_thai].mau}>{NHAN_TRANG_THAI_LO[l.trang_thai].nhan}</Tag> },
    { title: 'Khả dụng', dataIndex: 'kha_dung', key: 'kd', align: 'right' },
    ...(coChiTiet
      ? ([
          { title: 'Tồn', dataIndex: 'so_luong_ton', key: 'ton', align: 'right' },
          { title: 'Đang giữ', dataIndex: 'so_luong_giu', key: 'giu', align: 'right' },
          { title: 'Biệt trữ', dataIndex: 'so_luong_biet_tru', key: 'bt', align: 'right' },
          { title: 'Giá nhập', key: 'gia', align: 'right', render: (_, l) => dinhDangTien(l.gia_nhap) },
        ] as ColumnsType<Lo>)
      : []),
  ]
  return <Table<Lo> size="small" rowKey="lo_id" columns={cot} dataSource={q.data ?? []} loading={q.isLoading} pagination={false} />
}

/** KHO05: tồn kho theo sản phẩm, mở rộng ra từng lô. Dược sĩ chỉ thấy tồn khả dụng (backend ẩn giá nhập, đang giữ, biệt trữ). */
export default function TrangTonKho() {
  const [q, setQ] = useState('')
  const [chiThap, setChiThap] = useState(false)
  const [trang, setTrang] = useState(1)
  const ds = useQuery({
    queryKey: ['nhan-vien', 'ton-kho', q, chiThap, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/ton-kho', { params: { query: { q: q.trim() || undefined, chi_thap: chiThap, trang, kich_thuoc: 20 } } })
      if (error || !data) throw error ?? new Error('Không tải được tồn kho')
      return data
    },
    placeholderData: (truoc) => truoc,
  })
  const coChiTiet = (ds.data?.du_lieu ?? []).some((t) => t.tong_ton !== null)
  const cot: ColumnsType<Ton> = [
    { title: 'Sản phẩm', key: 'sp', render: (_, t) => <span>{t.ten} <Typography.Text type="secondary">{t.sku}</Typography.Text></span> },
    { title: 'Khả dụng', key: 'kd', align: 'right', render: (_, t) => <span>{t.ton_kha_dung} {t.don_vi_co_so} {t.thap && <Tag color="red">Tồn thấp</Tag>}</span> },
    ...(coChiTiet
      ? ([
          { title: 'Tổng tồn', dataIndex: 'tong_ton', key: 'ton', align: 'right' },
          { title: 'Đang giữ', dataIndex: 'tong_giu', key: 'giu', align: 'right' },
          { title: 'Biệt trữ', dataIndex: 'tong_biet_tru', key: 'bt', align: 'right' },
        ] as ColumnsType<Ton>)
      : []),
    { title: 'Mức tối thiểu', dataIndex: 'ton_toi_thieu', key: 'min', align: 'right' },
    { title: 'Số lô', dataIndex: 'so_lo', key: 'solo', align: 'right' },
  ]
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Input.Search allowClear placeholder="Tên hoặc SKU" style={{ width: 300 }} onSearch={(v) => { setQ(v); setTrang(1) }} />
        <label>
          <Switch checked={chiThap} onChange={(v) => { setChiThap(v); setTrang(1) }} /> Chỉ tồn thấp
        </label>
      </Space>
      {ds.isError && <Alert type="error" showIcon message="Không tải được tồn kho" />}
      <Table<Ton>
        rowKey="san_pham_id"
        columns={cot}
        dataSource={ds.data?.du_lieu ?? []}
        loading={ds.isLoading}
        expandable={{ expandedRowRender: (t) => <BangLo id={t.san_pham_id} />, rowExpandable: (t) => t.so_lo > 0 }}
        pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }}
      />
    </Space>
  )
}
