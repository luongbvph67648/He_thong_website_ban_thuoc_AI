import { useQuery } from '@tanstack/react-query'
import { Alert, Card, DatePicker, Descriptions, Drawer, Select, Space, Statistic, Table, Tabs, Tag, Typography } from 'antd'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { HoiThoaiAnDanh } from '../../../components/HoiThoaiAnDanh'
import dayjs from '../../../lib/dayjs'
import { dinhDangNgay } from '../../../lib/dinhDang'

type Tom = components['schemas']['HoiThoaiAnDanhTom']
type Khoang = [Dayjs, Dayjs]

const KICH_THUOC = 20
const KHOA = ['noi-bo', 'giam-sat-ai'] as const
const NHAN_Y_DINH: Record<string, string> = {
  hoi_san_pham: 'Hỏi sản phẩm',
  cach_dung: 'Cách dùng',
  trieu_chung: 'Triệu chứng',
  chinh_sach: 'Chính sách',
  don_hang: 'Đơn hàng',
  can_duoc_si: 'Cần dược sĩ',
  ngoai_pham_vi: 'Ngoài phạm vi',
  khac: 'Khác',
}
const macDinh = (): Khoang => [dayjs().subtract(29, 'day'), dayjs()]
const tham = (k: Khoang) => ({ tu_ngay: k[0].format('YYYY-MM-DD'), den_ngay: k[1].format('YYYY-MM-DD') })
const phanTram = (v: string | null) => (v === null ? '—' : `${(Number(v) * 100).toFixed(1)}%`)

function ThongKe({ khoang }: { khoang: Khoang }) {
  const tk = useQuery({
    queryKey: [...KHOA, 'thong-ke', tham(khoang)],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/giam-sat-ai/thong-ke', { params: { query: tham(khoang) } })
      if (error || !data) throw error ?? new Error('Không tải được thống kê')
      return data
    },
  })
  if (tk.isError) return <Alert type="error" showIcon title="Không tải được thống kê" />
  const d = tk.data
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap size="large">
        <Statistic title="Số hội thoại" value={d?.tong_hoi_thoai ?? '—'} loading={tk.isLoading} />
        <Statistic title="Tỉ lệ chuyển dược sĩ" value={phanTram(d?.ty_le_chuyen_duoc_si ?? null)} loading={tk.isLoading} />
        <Statistic title="Bị gắn cờ" value={d?.so_gan_co ?? '—'} loading={tk.isLoading} />
        <Statistic title="Token" value={d?.tong_token ?? '—'} loading={tk.isLoading} />
        <Statistic title="Chi phí (USD)" value={d?.tong_chi_phi_usd ?? '—'} formatter={(v) => String(v)} loading={tk.isLoading} />
      </Space>
      <Card size="small" title="Câu hỏi phổ biến theo ý định">
        <Table
          size="small"
          pagination={false}
          rowKey="y_dinh"
          dataSource={d?.cau_hoi_pho_bien ?? []}
          locale={{ emptyText: 'Chưa có dữ liệu' }}
          columns={[
            { title: 'Ý định', dataIndex: 'y_dinh', render: (v: string) => NHAN_Y_DINH[v] ?? v },
            { title: 'Số câu hỏi', dataIndex: 'so_luong', align: 'right' },
          ]}
        />
      </Card>
      {d && (
        <Descriptions bordered size="small" column={2} title="Đánh giá câu trả lời">
          <Descriptions.Item label="Khách: hữu ích">{d.danh_gia.khach_huu_ich}</Descriptions.Item>
          <Descriptions.Item label="Khách: không hữu ích">{d.danh_gia.khach_khong_huu_ich}</Descriptions.Item>
          <Descriptions.Item label="Dược sĩ: đúng">{d.danh_gia.duoc_si_dung}</Descriptions.Item>
          <Descriptions.Item label="Dược sĩ: sai">{d.danh_gia.duoc_si_sai}</Descriptions.Item>
        </Descriptions>
      )}
    </Space>
  )
}

function HoiThoai({ khoang }: { khoang: Khoang }) {
  const [trang, setTrang] = useState(1)
  const [ganCo, setGanCo] = useState<boolean | undefined>(undefined)
  const [chuyen, setChuyen] = useState<boolean | undefined>(undefined)
  const [mo, setMo] = useState<number | null>(null)
  const ds = useQuery({
    queryKey: [...KHOA, 'hoi-thoai', tham(khoang), ganCo, chuyen, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/giam-sat-ai/hoi-thoai', {
        params: { query: { ...tham(khoang), bi_gan_co: ganCo, da_chuyen_duoc_si: chuyen, trang, kich_thuoc: KICH_THUOC } },
      })
      if (error || !data) throw error ?? new Error('Không tải được hội thoại')
      return data
    },
  })
  const ct = useQuery({
    queryKey: [...KHOA, 'ct', mo],
    enabled: mo !== null,
    staleTime: Infinity,
    gcTime: 0,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/giam-sat-ai/hoi-thoai/{hoi_thoai_id}', { params: { path: { hoi_thoai_id: mo! } } })
      if (error || !data) throw error ?? new Error('Không mở được hội thoại')
      return data
    },
  })
  const loc = (setter: (v: boolean | undefined) => void) => (v: string) => { setter(v === 'co' ? true : v === 'khong' ? false : undefined); setTrang(1) }
  const tuy = (g: boolean | undefined) => (g === undefined ? 'tat_ca' : g ? 'co' : 'khong')
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Select aria-label="Lọc gắn cờ" style={{ width: 180 }} value={tuy(ganCo)} onChange={loc(setGanCo)} options={[{ value: 'tat_ca', label: 'Gắn cờ: tất cả' }, { value: 'co', label: 'Chỉ bị gắn cờ' }, { value: 'khong', label: 'Không bị gắn cờ' }]} />
        <Select aria-label="Lọc chuyển dược sĩ" style={{ width: 200 }} value={tuy(chuyen)} onChange={loc(setChuyen)} options={[{ value: 'tat_ca', label: 'Chuyển dược sĩ: tất cả' }, { value: 'co', label: 'Đã chuyển dược sĩ' }, { value: 'khong', label: 'Chỉ trả lời bằng AI' }]} />
      </Space>
      {ds.isError && <Alert type="error" showIcon title="Không tải được hội thoại" />}
      <Table<Tom>
        rowKey="id"
        size="small"
        loading={ds.isLoading}
        dataSource={ds.data?.du_lieu ?? []}
        locale={{ emptyText: 'Không có hội thoại nào' }}
        pagination={{ current: trang, pageSize: KICH_THUOC, total: ds.data?.tong ?? 0, showSizeChanger: false, onChange: setTrang }}
        onRow={(r) => ({ onClick: () => setMo(r.id), style: { cursor: 'pointer' } })}
        columns={[
          { title: 'Thời điểm', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          { title: 'Câu hỏi đầu (đã ẩn danh)', dataIndex: 'cau_hoi_dau', ellipsis: true },
          { title: 'Tin', dataIndex: 'so_tin_nhan', align: 'right', width: 60 },
          { title: 'Trạng thái', render: (_, r) => <Space size={4} wrap>{r.loai === 'duoc_si' && <Tag color="blue">Dược sĩ</Tag>}{r.bi_gan_co && <Tag color="red">Nguy hiểm</Tag>}{r.so_khach_bao_sai > 0 && <Tag color="orange">Khách báo sai</Tag>}</Space> },
          { title: 'Token', dataIndex: 'tong_token', align: 'right' },
          { title: 'USD', dataIndex: 'chi_phi', align: 'right' },
        ]}
      />
      <Drawer title="Hội thoại (đã ẩn danh)" size={640} open={mo !== null} onClose={() => setMo(null)} destroyOnHidden>
        {ct.isError && <Alert type="error" showIcon title="Không mở được hội thoại" />}
        {ct.data && <HoiThoaiAnDanh tin={ct.data.tin_nhan} />}
      </Drawer>
    </Space>
  )
}

function TimKiemKhongKetQua({ khoang }: { khoang: Khoang }) {
  const q = useQuery({
    queryKey: [...KHOA, 'tim-kiem', tham(khoang)],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/giam-sat-ai/tim-kiem-khong-ket-qua', { params: { query: tham(khoang) } })
      if (error || !data) throw error ?? new Error('Không tải được dữ liệu')
      return data
    },
  })
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>Từ khóa khách tìm mà không ra sản phẩm: nên bổ sung sản phẩm, tên khác của hoạt chất hoặc từ đồng nghĩa.</Typography.Paragraph>
      {q.isError && <Alert type="error" showIcon title="Không tải được dữ liệu" />}
      <Table
        rowKey="tu_khoa"
        size="small"
        loading={q.isLoading}
        dataSource={q.data ?? []}
        pagination={false}
        locale={{ emptyText: 'Không có từ khóa nào không ra kết quả' }}
        columns={[
          { title: 'Từ khóa', dataIndex: 'tu_khoa' },
          { title: 'Số lần', dataIndex: 'so_lan', align: 'right' },
          { title: 'Lần cuối', dataIndex: 'lan_cuoi', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
        ]}
      />
    </Space>
  )
}

/** AD11: giám sát hội thoại AI đã ẩn danh, thống kê (ý định, tỉ lệ chuyển dược sĩ, chi phí) và từ khóa tìm không có kết quả. */
export default function TrangGiamSatAi() {
  const [khoang, setKhoang] = useState<Khoang>(macDinh)
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Giám sát AI</Typography.Title>
      <DatePicker.RangePicker
        allowClear={false}
        value={khoang}
        format="DD/MM/YYYY"
        disabledDate={(d) => d.isAfter(dayjs(), 'day')}
        onChange={(v) => v?.[0] && v[1] && setKhoang([v[0], v[1]])}
      />
      <Tabs
        destroyOnHidden
        items={[
          { key: 'thong-ke', label: 'Thống kê', children: <ThongKe khoang={khoang} /> },
          { key: 'hoi-thoai', label: 'Hội thoại', children: <HoiThoai khoang={khoang} /> },
          { key: 'tim-kiem', label: 'Tìm kiếm không có kết quả', children: <TimKiemKhongKetQua khoang={khoang} /> },
        ]}
      />
    </Space>
  )
}
