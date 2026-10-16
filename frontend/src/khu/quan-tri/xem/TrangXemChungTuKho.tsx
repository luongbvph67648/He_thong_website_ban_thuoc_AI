import { useQuery } from '@tanstack/react-query'
import { Alert, Select, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'

type Ct = components['schemas']['ChungTuKho']
type Loai = Ct['loai']

const NHAN_LOAI: Record<Loai, string> = { phieu_nhap: 'Phiếu nhập', kiem_ke: 'Kiểm kê', dieu_chinh: 'Điều chỉnh tồn', phieu_huy: 'Phiếu hủy', xuat_tra: 'Xuất trả NCC' }
const NHAN_TT: Record<string, { nhan: string; mau: string }> = {
  cho_duyet: { nhan: 'Chờ duyệt', mau: 'gold' }, da_duyet: { nhan: 'Đã duyệt', mau: 'green' }, tu_choi: { nhan: 'Từ chối', mau: 'red' },
  dang_kiem: { nhan: 'Đang kiểm', mau: 'blue' }, da_chot: { nhan: 'Đã chốt', mau: 'green' },
}
const KICH_THUOC = 20

/** AD16: Admin xem gộp chứng từ kho (chỉ xem, không có thao tác ghi). */
export default function TrangXemChungTuKho() {
  const [loai, setLoai] = useState<Loai | undefined>()
  const [trang, setTrang] = useState(1)
  const ds = useQuery({
    queryKey: ['quan-tri', 'xem', 'chung-tu-kho', loai, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/chung-tu-kho', { params: { query: { loai, trang, kich_thuoc: KICH_THUOC } } })
      if (error || !data) throw error ?? new Error('Không tải được chứng từ')
      return data
    },
  })
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Chứng từ kho</Typography.Title>
      <Alert type="info" showIcon title="Chỉ xem. Việc lập phiếu thuộc nhân viên kho, duyệt phiếu ở màn Duyệt phiếu kho." />
      <Select allowClear placeholder="Mọi loại" style={{ width: 220 }} value={loai} onChange={(v) => { setLoai(v); setTrang(1) }} options={(Object.keys(NHAN_LOAI) as Loai[]).map((k) => ({ value: k, label: NHAN_LOAI[k] }))} />
      <Table<Ct>
        rowKey={(r) => `${r.loai}-${r.id}`}
        size="small"
        loading={ds.isLoading}
        dataSource={ds.data?.du_lieu ?? []}
        locale={{ emptyText: 'Chưa có chứng từ' }}
        pagination={{ current: trang, pageSize: KICH_THUOC, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }}
        expandable={{ expandedRowRender: (r) => <Typography.Text>{r.ghi_chu ?? 'Không có ghi chú'}</Typography.Text>, rowExpandable: (r) => !!r.ghi_chu }}
        columns={[
          { title: 'Loại', dataIndex: 'loai', render: (v: Loai) => NHAN_LOAI[v] },
          { title: 'Mã phiếu', dataIndex: 'ma_phieu' },
          { title: 'Trạng thái', dataIndex: 'trang_thai', render: (v: string | null) => (v ? <Tag color={NHAN_TT[v]?.mau}>{NHAN_TT[v]?.nhan ?? v}</Tag> : '—') },
          { title: 'Người lập', dataIndex: 'nguoi_lap' },
          { title: 'Người duyệt', dataIndex: 'nguoi_duyet', render: (v: string | null) => v ?? '—' },
          { title: 'Ngày', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
        ]}
      />
    </Space>
  )
}
