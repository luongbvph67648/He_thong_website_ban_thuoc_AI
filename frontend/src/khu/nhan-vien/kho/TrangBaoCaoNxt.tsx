import { DownloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { App, Alert, Button, DatePicker, Input, Segmented, Select, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import dayjs from '../../../lib/dayjs'

type Dong = components['schemas']['DongNxt']
type Nhom = 'san_pham' | 'lo'
type Khu = 'kho_ban' | 'biet_tru'

const so = (v: number) => v.toLocaleString('vi-VN')

/** KHO13: báo cáo nhập - xuất - tồn theo kỳ, tính từ thẻ kho. Số có dấu: nhập dương, xuất âm. */
export default function TrangBaoCaoNxt() {
  const { message } = App.useApp()
  const [ky, setKy] = useState<[Dayjs, Dayjs]>([dayjs().subtract(29, 'day'), dayjs()])
  const [nhom, setNhom] = useState<Nhom>('san_pham')
  const [khu, setKhu] = useState<Khu>('kho_ban')
  const [q, setQ] = useState('')
  const [trang, setTrang] = useState(1)
  const [dangXuat, setDangXuat] = useState(false)
  const loc = { tu_ngay: ky[0].format('YYYY-MM-DD'), den_ngay: ky[1].format('YYYY-MM-DD'), khu, nhom, q: q.trim() || undefined }

  const ds = useQuery({
    queryKey: ['nhan-vien', 'bao-cao-nxt', loc, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/bao-cao/nhap-xuat-ton', { params: { query: { ...loc, trang, kich_thuoc: 20 } } })
      if (error || !data) throw error ?? new Error('Không tải được báo cáo')
      return data
    },
    placeholderData: (truoc) => truoc,
  })

  async function xuatExcel() {
    setDangXuat(true)
    try {
      const { data, error } = await api.GET('/api/v1/noi-bo/bao-cao/nhap-xuat-ton/excel', { params: { query: loc }, parseAs: 'blob' })
      if (error || !data) throw error ?? new Error('Xuất Excel thất bại')
      const url = URL.createObjectURL(data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `nhap-xuat-ton_${loc.tu_ngay}_${loc.den_ngay}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      message.error('Không xuất được file Excel (quá nhiều dòng hoặc kỳ không hợp lệ)')
    } finally {
      setDangXuat(false)
    }
  }

  const so_cot = (tieu: string, k: keyof Dong): ColumnsType<Dong>[number] => ({ title: tieu, dataIndex: k, key: k, align: 'right', render: (v: number) => so(v) })
  const cot: ColumnsType<Dong> = [
    { title: 'Sản phẩm', key: 'sp', render: (_, d) => <span>{d.ten} <Typography.Text type="secondary">{d.sku}</Typography.Text></span> },
    ...(nhom === 'lo'
      ? ([
          { title: 'Số lô', dataIndex: 'so_lo', key: 'lo' },
          { title: 'HSD', key: 'hsd', render: (_, d) => (d.han_su_dung ? dinhDangNgay(d.han_su_dung) : '') },
        ] as ColumnsType<Dong>)
      : []),
    so_cot('Tồn đầu', 'ton_dau'),
    so_cot('Nhập kho', 'nhap_kho'),
    so_cot('Hoàn nhập', 'hoan_nhap'),
    so_cot('Nhận trả về', 'nhan_tra_ve'),
    so_cot('Điều chỉnh', 'dieu_chinh'),
    so_cot('Xuất bán', 'xuat_ban'),
    so_cot('Hủy', 'huy_hang'),
    so_cot('Xuất trả NCC', 'xuat_tra_ncc'),
    { ...so_cot('Tồn cuối', 'ton_cuoi'), fixed: 'right' },
  ]
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <DatePicker.RangePicker
          allowClear={false}
          format="DD/MM/YYYY"
          value={ky}
          onChange={(v) => { if (v?.[0] && v[1]) { setKy([v[0], v[1]]); setTrang(1) } }}
        />
        <Segmented<Nhom> value={nhom} onChange={(v) => { setNhom(v); setTrang(1) }} options={[{ value: 'san_pham', label: 'Theo sản phẩm' }, { value: 'lo', label: 'Theo lô' }]} />
        <Select<Khu> value={khu} onChange={(v) => { setKhu(v); setTrang(1) }} style={{ width: 150 }} options={[{ value: 'kho_ban', label: 'Kho bán' }, { value: 'biet_tru', label: 'Biệt trữ' }]} />
        <Input.Search allowClear placeholder="Tên hoặc SKU" style={{ width: 240 }} onSearch={(v) => { setQ(v); setTrang(1) }} />
        <Button icon={<DownloadOutlined />} loading={dangXuat} onClick={xuatExcel}>Xuất Excel</Button>
      </Space>
      {ds.isError && <Alert type="error" showIcon message="Không tải được báo cáo" />}
      <Table<Dong>
        size="small"
        rowKey={(d) => `${d.san_pham_id}-${d.lo_id ?? 0}`}
        columns={cot}
        dataSource={ds.data?.du_lieu ?? []}
        loading={ds.isLoading}
        scroll={{ x: 'max-content' }}
        pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }}
      />
      <Typography.Text type="secondary">Tồn cuối = tồn đầu + tổng biến động trong kỳ (nhập dương, xuất âm), tính từ thẻ kho theo giờ Việt Nam.</Typography.Text>
    </Space>
  )
}
