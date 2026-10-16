import { useQuery } from '@tanstack/react-query'
import { Alert, DatePicker, Input, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import dayjs from '../../../lib/dayjs'
import { nhanHanhDong } from '../../../lib/nhatKy'
import { SoSanhGiaTri } from './SoSanhGiaTri'

type DongNhatKy = components['schemas']['NhatKyDoc']

const KICH_THUOC = 20
const ID_TOI_DA = 2_147_483_647
const KHOA_QUERY = ['noi-bo', 'nhat-ky'] as const

function docNgay(gia: string | null): string | undefined {
  const khop = gia ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(gia) : null
  if (!khop) return undefined
  const [nam, thang, ngay] = [Number(khop[1]), Number(khop[2]), Number(khop[3])]
  const d = new Date(Date.UTC(nam, thang - 1, ngay))
  return d.getUTCFullYear() === nam && d.getUTCMonth() === thang - 1 && d.getUTCDate() === ngay ? gia! : undefined
}

function docSoNguyen(gia: string | null, toiDa: number): number | undefined {
  if (!gia || !/^[1-9]\d{0,9}$/.test(gia)) return undefined
  const so = Number(gia)
  return so <= toiDa ? so : undefined
}

/** Nhật ký hệ thống (AD15): tra cứu theo bảng, bản ghi, người thực hiện, hành động, khoảng ngày; mở dòng để xem cũ/mới. Chỉ đọc. */
export default function TrangNhatKy() {
  const [tham, datTham] = useSearchParams()
  const bang = tham.get('bang') || undefined
  const hanhDong = tham.get('hanh_dong') || undefined
  const banGhiId = tham.get('ban_ghi_id') || undefined
  const nhanVienId = docSoNguyen(tham.get('nhan_vien_id'), ID_TOI_DA)
  const tuNgay = docNgay(tham.get('tu_ngay'))
  const denNgay = docNgay(tham.get('den_ngay'))
  const trang = docSoNguyen(tham.get('trang'), 1_000_000) ?? 1

  const doiThamSo = (thayDoi: Record<string, string | undefined>) => {
    const moi = new URLSearchParams(tham)
    for (const [k, v] of Object.entries({ trang: undefined, ...thayDoi })) {
      if (v) moi.set(k, v)
      else moi.delete(k)
    }
    datTham(moi, { replace: true })
  }

  const nhatKy = useQuery({
    queryKey: [...KHOA_QUERY, 'danh-sach', { bang, hanhDong, banGhiId, nhanVienId, tuNgay, denNgay, trang }],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/nhat-ky', {
        params: { query: { bang, ban_ghi_id: banGhiId, nhan_vien_id: nhanVienId, hanh_dong: hanhDong, tu_ngay: tuNgay, den_ngay: denNgay, trang, kich_thuoc: KICH_THUOC } },
      })
      if (error) throw error
      return data
    },
  })
  const giaTriLoc = useQuery({
    queryKey: [...KHOA_QUERY, 'gia-tri-loc'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/nhat-ky/gia-tri-loc')
      if (error) throw error
      return data
    },
  })
  const nhanVien = useQuery({
    queryKey: ['noi-bo', 'nhan-vien', 'cho-bo-loc'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/nhan-vien', { params: { query: { kich_thuoc: 100 } } })
      if (error) throw error
      return data
    },
  })

  const cot: ColumnsType<DongNhatKy> = [
    { title: 'Thời gian', key: 'thoi_gian', render: (_, d) => dinhDangNgay(d.created_at, 'ngayGioGiay') },
    {
      title: 'Người thực hiện',
      key: 'nhan_vien',
      render: (_, d) => (d.nhan_vien ? `${d.nhan_vien.ho_ten} (${d.nhan_vien.ma_nhan_vien})` : <Typography.Text type="secondary">Hệ thống hoặc chưa xác định</Typography.Text>),
    },
    { title: 'Hành động', key: 'hanh_dong', render: (_, d) => <Tag>{nhanHanhDong(d.hanh_dong)}</Tag> },
    { title: 'Bảng', key: 'bang', render: (_, d) => <code>{d.bang}</code> },
    { title: 'Bản ghi', key: 'ban_ghi_id', render: (_, d) => d.ban_ghi_id ?? '—' },
    { title: 'IP', key: 'ip', render: (_, d) => d.ip ?? '—' },
  ]

  const khoangNgay: [Dayjs, Dayjs] | null = tuNgay && denNgay ? [dayjs(tuNgay), dayjs(denNgay)] : null

  return (
    <div>
      <Typography.Title level={3}>Nhật ký hệ thống</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          allowClear
          showSearch
          placeholder="Bảng"
          style={{ width: 180 }}
          value={bang}
          options={(giaTriLoc.data?.bang ?? []).map((b) => ({ value: b, label: b }))}
          onChange={(v: string | undefined) => doiThamSo({ bang: v })}
          aria-label="Lọc theo bảng"
        />
        <Select
          allowClear
          placeholder="Hành động"
          style={{ width: 200 }}
          value={hanhDong}
          options={(giaTriLoc.data?.hanh_dong ?? []).map((h) => ({ value: h, label: nhanHanhDong(h) }))}
          onChange={(v: string | undefined) => doiThamSo({ hanh_dong: v })}
          aria-label="Lọc theo hành động"
        />
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="Người thực hiện"
          style={{ width: 240 }}
          value={nhanVienId}
          options={(nhanVien.data?.du_lieu ?? []).map((n) => ({ value: n.id, label: `${n.ma_nhan_vien} · ${n.ho_ten}` }))}
          onChange={(v: number | undefined) => doiThamSo({ nhan_vien_id: v === undefined ? undefined : String(v) })}
          aria-label="Lọc theo người thực hiện"
        />
        <Input.Search key={banGhiId} defaultValue={banGhiId} allowClear placeholder="Id bản ghi" style={{ width: 200 }} maxLength={60} onSearch={(v) => doiThamSo({ ban_ghi_id: v.trim() || undefined })} />
        <DatePicker.RangePicker
          value={khoangNgay}
          format="DD/MM/YYYY"
          placeholder={['Từ ngày', 'Đến ngày']}
          allowClear
          onChange={(gia) => doiThamSo({ tu_ngay: gia?.[0]?.format('YYYY-MM-DD'), den_ngay: gia?.[1]?.format('YYYY-MM-DD') })}
        />
      </Space>

      {nhatKy.isError && <Alert type="error" showIcon title="Không tải được nhật ký hệ thống" style={{ marginBottom: 16 }} />}
      <Table<DongNhatKy>
        rowKey="id"
        size="middle"
        columns={cot}
        loading={nhatKy.isPending}
        dataSource={nhatKy.data?.du_lieu ?? []}
        expandable={{ expandedRowRender: (d) => <SoSanhGiaTri dong={d} /> }}
        pagination={{
          current: trang,
          pageSize: KICH_THUOC,
          total: nhatKy.data?.tong ?? 0,
          showSizeChanger: false,
          onChange: (t) => doiThamSo({ trang: t > 1 ? String(t) : undefined }),
        }}
        locale={{ emptyText: 'Không có dòng nhật ký phù hợp' }}
      />
    </div>
  )
}
