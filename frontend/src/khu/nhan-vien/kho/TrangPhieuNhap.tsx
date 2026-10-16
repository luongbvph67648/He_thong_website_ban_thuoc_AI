import { useQuery } from '@tanstack/react-query'
import { Alert, Button, DatePicker, Descriptions, Drawer, Input, Select, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'

type Phieu = components['schemas']['PhieuNhapTomTat']

/** KHO02: danh sách và xem chi tiết phiếu nhập. Phiếu đã lưu không sửa, không xóa. */
export default function TrangPhieuNhap() {
  const dieuHuong = useNavigate()
  const coGhi = coQuyen(usePhien((s) => s.quyen), 'stock.import')
  const [q, setQ] = useState('')
  const [nccId, setNccId] = useState<number | undefined>()
  const [khoang, setKhoang] = useState<[string, string] | null>(null)
  const [trang, setTrang] = useState(1)
  const [xem, setXem] = useState<number | null>(null)

  const nccDs = useQuery({
    queryKey: ['nhan-vien', 'nha-cung-cap', 'tat-ca'],
    queryFn: async () => (await api.GET('/api/v1/noi-bo/nha-cung-cap', { params: { query: { trang_thai: 'tat_ca', kich_thuoc: 100 } } })).data?.du_lieu ?? [],
  })
  const ds = useQuery({
    queryKey: ['nhan-vien', 'phieu-nhap', q, nccId, khoang, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/phieu-nhap', {
        params: { query: { q: q.trim() || undefined, nha_cung_cap_id: nccId, tu_ngay: khoang?.[0], den_ngay: khoang?.[1], trang, kich_thuoc: 20 } },
      })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
    placeholderData: (truoc) => truoc,
  })
  const chiTiet = useQuery({
    queryKey: ['nhan-vien', 'phieu-nhap', 'ct', xem],
    enabled: xem !== null,
    queryFn: async () => (await api.GET('/api/v1/noi-bo/phieu-nhap/{phieu_id}', { params: { path: { phieu_id: xem as number } } })).data,
  })

  const cot: ColumnsType<Phieu> = [
    { title: 'Mã phiếu', key: 'ma', render: (_, p) => <Button type="link" style={{ padding: 0 }} onClick={() => setXem(p.id)}>{p.ma_phieu}</Button> },
    { title: 'Ngày nhập', key: 'ngay', width: 160, render: (_, p) => dinhDangNgay(p.ngay_nhap, 'ngayGio') },
    { title: 'Nhà cung cấp', key: 'ncc', render: (_, p) => p.nha_cung_cap.ten },
    { title: 'Số hóa đơn', dataIndex: 'so_hoa_don_ncc', key: 'hd' },
    { title: 'Số dòng', dataIndex: 'so_dong', key: 'sd', width: 90, align: 'right' },
    { title: 'Tổng tiền', key: 'tien', width: 140, align: 'right', render: (_, p) => dinhDangTien(p.tong_tien) },
    { title: 'Người lập', key: 'nv', render: (_, p) => p.nhan_vien.ho_ten },
  ]

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Input.Search allowClear placeholder="Mã phiếu hoặc số hóa đơn" style={{ width: 260 }} onSearch={(v) => { setQ(v); setTrang(1) }} />
        <Select allowClear showSearch optionFilterProp="label" placeholder="Nhà cung cấp" style={{ width: 240 }} value={nccId} onChange={(v) => { setNccId(v); setTrang(1) }} options={(nccDs.data ?? []).map((n) => ({ value: n.id, label: n.ten }))} />
        <DatePicker.RangePicker onChange={(_, s) => { setKhoang(s[0] && s[1] ? [s[0], s[1]] : null); setTrang(1) }} />
        {coGhi && (
          <Button type="primary" onClick={() => dieuHuong('/nhan-vien/phieu-nhap/tao')}>
            Lập phiếu nhập
          </Button>
        )}
      </Space>
      {ds.isError && <Alert type="error" showIcon message="Không tải được danh sách phiếu nhập" />}
      <Table<Phieu> rowKey="id" columns={cot} dataSource={ds.data?.du_lieu ?? []} loading={ds.isLoading} pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }} />
      <Drawer title="Chi tiết phiếu nhập" open={xem !== null} onClose={() => setXem(null)} size="large" destroyOnHidden>
        {chiTiet.data && (
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="Mã phiếu">{chiTiet.data.ma_phieu}</Descriptions.Item>
              <Descriptions.Item label="Ngày nhập">{dinhDangNgay(chiTiet.data.ngay_nhap, 'ngayGio')}</Descriptions.Item>
              <Descriptions.Item label="Nhà cung cấp">{chiTiet.data.nha_cung_cap.ten}</Descriptions.Item>
              <Descriptions.Item label="Số hóa đơn">{chiTiet.data.so_hoa_don_ncc ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="Người lập">{chiTiet.data.nhan_vien.ho_ten}</Descriptions.Item>
              <Descriptions.Item label="Tổng tiền">{dinhDangTien(chiTiet.data.tong_tien)}</Descriptions.Item>
            </Descriptions>
            {chiTiet.data.ghi_chu && <Typography.Paragraph>{chiTiet.data.ghi_chu}</Typography.Paragraph>}
            <Table
              size="small"
              rowKey="lo_id"
              pagination={false}
              dataSource={chiTiet.data.dong}
              columns={[
                { title: 'Sản phẩm', key: 'sp', render: (_, d) => `${d.san_pham.ten} (${d.san_pham.sku})` },
                { title: 'Số lô', dataIndex: 'so_lo', key: 'lo' },
                { title: 'HSD', key: 'hsd', render: (_, d) => dinhDangNgay(d.han_su_dung) },
                { title: 'Số lượng', key: 'sl', align: 'right', render: (_, d) => `${d.so_luong} ${d.don_vi.ten_don_vi} (${d.so_luong_co_so})` },
                { title: 'Giá nhập', key: 'gia', align: 'right', render: (_, d) => dinhDangTien(d.gia_nhap) },
                { title: 'Thành tiền', key: 'tt', align: 'right', render: (_, d) => dinhDangTien(d.thanh_tien) },
              ]}
            />
          </Space>
        )}
      </Drawer>
    </Space>
  )
}
