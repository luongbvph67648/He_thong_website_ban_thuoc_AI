import { useQuery } from '@tanstack/react-query'
import { Alert, DatePicker, Input, Select, Space, Table, Tag } from 'antd'
import { useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { NHAN_PHUONG_THUC_DON } from '../../../lib/donHang'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { TRANG_THAI, nhanTrangThai } from '../../../lib/trangThai'

type Don = components['schemas']['DonNoiBoTomTat']
type TrangThai = components['schemas']['TrangThaiDon']
type KenhBan = components['schemas']['KenhBan']
type PhuongThuc = components['schemas']['PhuongThucThanhToan']

const tuyChon = (m: Record<string, { nhan: string }>) => Object.keys(m).map((k) => ({ value: k, label: m[k].nhan }))

/** DS01: danh sách đơn nội bộ, lọc theo trạng thái, ngày đặt, phương thức thanh toán, kênh bán và mã/tên/SĐT. */
export default function TrangQuanLyDon() {
  const goc = useLocation().pathname.replace(/\/+$/, '')
  const [thamSo] = useSearchParams()
  // `?trang_thai=` (liên kết từ trang Tổng quan) chỉ đặt bộ lọc ban đầu; giá trị lạ bị bỏ.
  const [trangThai, setTrangThai] = useState<TrangThai | undefined>(() => {
    const v = thamSo.get('trang_thai')
    return v && Object.hasOwn(TRANG_THAI.don_hang, v) ? (v as TrangThai) : undefined
  })
  const [kenh, setKenh] = useState<KenhBan | undefined>()
  const [phuongThuc, setPhuongThuc] = useState<PhuongThuc | undefined>()
  const [khoang, setKhoang] = useState<[string, string] | null>(null)
  const [q, setQ] = useState('')
  const [trang, setTrang] = useState(1)
  const ds = useQuery({
    queryKey: ['nhan-vien', 'don-hang', trangThai, kenh, phuongThuc, khoang, q, trang],
    placeholderData: (truoc) => truoc,
    queryFn: async () => {
      const query = {
        trang_thai: trangThai,
        kenh_ban: kenh,
        phuong_thuc_tt: phuongThuc,
        tu_ngay: khoang?.[0],
        den_ngay: khoang?.[1],
        q: q.trim() || undefined,
        trang,
        kich_thuoc: 20,
      }
      const { data, error } = await api.GET('/api/v1/noi-bo/don-hang', { params: { query } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách đơn')
      return data
    },
  })
  const loc = <T,>(dat: (v: T | undefined) => void) => (v: T | undefined) => { dat(v); setTrang(1) }
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Input.Search allowClear placeholder="Mã đơn, tên hoặc SĐT người nhận" style={{ width: 280 }} onSearch={(v) => { setQ(v); setTrang(1) }} />
        <Select<TrangThai> allowClear placeholder="Trạng thái" style={{ width: 190 }} value={trangThai} onChange={loc(setTrangThai)} options={tuyChon(TRANG_THAI.don_hang)} />
        <Select<PhuongThuc> allowClear placeholder="Thanh toán" style={{ width: 150 }} value={phuongThuc} onChange={loc(setPhuongThuc)} options={Object.entries(NHAN_PHUONG_THUC_DON).map(([value, label]) => ({ value: value as PhuongThuc, label }))} />
        <Select<KenhBan> allowClear placeholder="Kênh bán" style={{ width: 140 }} value={kenh} onChange={loc(setKenh)} options={tuyChon(TRANG_THAI.kenh_ban)} />
        <DatePicker.RangePicker format="DD/MM/YYYY" onChange={(_, s) => { setKhoang(s[0] && s[1] ? [dinhNgayIso(s[0]), dinhNgayIso(s[1])] : null); setTrang(1) }} />
      </Space>
      {ds.isError && <Alert type="error" showIcon message="Không tải được danh sách đơn hàng" />}
      <Table<Don>
        rowKey="id"
        loading={ds.isLoading}
        dataSource={ds.data?.du_lieu ?? []}
        pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }}
        columns={[
          { title: 'Mã đơn', key: 'ma', render: (_, d) => <Link to={`${goc}/${d.id}`}>{d.ma_don}</Link> },
          { title: 'Ngày đặt', key: 'ngay', render: (_, d) => dinhDangNgay(d.created_at, 'ngayGio') },
          { title: 'Người nhận', key: 'nguoi', render: (_, d) => [d.ten_nguoi_nhan, d.sdt_nguoi_nhan].filter(Boolean).join(' · ') || '—' },
          { title: 'Kênh', key: 'kenh', render: (_, d) => nhanTrangThai('kenh_ban', d.kenh_ban).nhan },
          { title: 'Thanh toán', key: 'pt', render: (_, d) => (d.phuong_thuc_tt ? (NHAN_PHUONG_THUC_DON[d.phuong_thuc_tt] ?? d.phuong_thuc_tt) : '—') },
          { title: 'Tổng tiền', key: 'tien', align: 'right', render: (_, d) => dinhDangTien(d.tong_tien) },
          { title: 'Trạng thái', key: 'tt', render: (_, d) => { const n = nhanTrangThai('don_hang', d.trang_thai); return <Tag color={n.mau}>{n.nhan}</Tag> } },
        ]}
      />
    </Space>
  )
}

/** `DD/MM/YYYY` (định dạng hiển thị của RangePicker) sang `YYYY-MM-DD` cho API. */
function dinhNgayIso(s: string): string {
  const [d, m, y] = s.split('/')
  return `${y}-${m}-${d}`
}
