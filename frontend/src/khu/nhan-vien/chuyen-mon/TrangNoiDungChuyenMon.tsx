import { useQuery } from '@tanstack/react-query'
import { Alert, Input, Segmented, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { NhanTrangThai } from '../../../components/NhanTrangThai'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { KHOA_QUERY_CHUYEN_MON, type DongNoiDung } from './noiDung'

const KICH_THUOC = 20
const BO_LOC = [
  { value: 'tat_ca', label: 'Tất cả' },
  { value: 'cho_duyet', label: 'Chờ duyệt' },
  { value: 'da_duyet', label: 'Đã có nội dung duyệt' },
  { value: 'chua_co_noi_dung', label: 'Chưa có nội dung duyệt' },
] as const
type Loc = (typeof BO_LOC)[number]['value']

/** Danh sách sản phẩm theo tình trạng nội dung chuyên môn (DS10). Bộ lọc nằm trên URL. */
export default function TrangNoiDungChuyenMon() {
  const [tham, datTham] = useSearchParams()
  const gocTrang = useLocation().pathname.replace(/\/+$/, '')
  const q = tham.get('q') ?? ''
  const loc: Loc = BO_LOC.find((o) => o.value === tham.get('loc'))?.value ?? 'tat_ca'
  const trang = Math.max(1, Number(tham.get('trang')) || 1)

  const doiThamSo = (thayDoi: Record<string, string | undefined>) => {
    const moi = new URLSearchParams(tham)
    for (const [k, v] of Object.entries({ trang: undefined, ...thayDoi })) {
      if (v) moi.set(k, v)
      else moi.delete(k)
    }
    datTham(moi, { replace: true })
  }

  const danhSach = useQuery({
    queryKey: [...KHOA_QUERY_CHUYEN_MON, 'danh-sach', { q, loc, trang }],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/chuyen-mon', {
        params: { query: { q: q || undefined, loc: loc === 'tat_ca' ? undefined : loc, trang, kich_thuoc: KICH_THUOC } },
      })
      if (error) throw error
      return data
    },
  })

  const cot: ColumnsType<DongNoiDung> = [
    { title: 'SKU', dataIndex: 'sku', key: 'sku', width: 140 },
    { title: 'Sản phẩm', key: 'ten', render: (_, d) => <Link to={`${gocTrang}/${d.san_pham_id}`}>{d.ten}</Link> },
    { title: 'Loại', key: 'loai', render: (_, d) => <NhanTrangThai loai="loai_san_pham" giaTri={d.loai_san_pham} /> },
    {
      title: 'Đang hiển thị',
      key: 'hien_thi',
      render: (_, d) =>
        d.phien_ban_da_duyet === null ? (
          <Typography.Text type="secondary">Chưa có</Typography.Text>
        ) : (
          <span>
            Bản {d.phien_ban_da_duyet}
            {d.ngay_duyet && <Typography.Text type="secondary"> · duyệt {dinhDangNgay(d.ngay_duyet, 'ngay')}</Typography.Text>}
          </span>
        ),
    },
    {
      title: 'Chờ duyệt',
      key: 'cho_duyet',
      render: (_, d) => (d.cho_duyet ? <Tag color="processing">Bản nháp {d.phien_ban_nhap_moi_nhat}</Tag> : <span aria-hidden>—</span>),
    },
  ]

  return (
    <div>
      <Typography.Title level={3}>Nội dung chuyên môn</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search key={q} defaultValue={q} allowClear placeholder="Tìm theo tên hoặc SKU" style={{ width: 300 }} onSearch={(v) => doiThamSo({ q: v.trim() || undefined })} />
        <Segmented<Loc> options={[...BO_LOC]} value={loc} onChange={(v) => doiThamSo({ loc: v === 'tat_ca' ? undefined : v })} />
      </Space>
      {danhSach.isError && <Alert type="error" showIcon title="Không tải được danh sách sản phẩm" style={{ marginBottom: 16 }} />}
      <Table<DongNoiDung>
        rowKey="san_pham_id"
        columns={cot}
        loading={danhSach.isPending}
        dataSource={danhSach.data?.du_lieu ?? []}
        pagination={{
          current: trang,
          pageSize: KICH_THUOC,
          total: danhSach.data?.tong ?? 0,
          showSizeChanger: false,
          onChange: (t) => doiThamSo({ trang: t > 1 ? String(t) : undefined }),
        }}
        locale={{ emptyText: 'Không có sản phẩm phù hợp' }}
      />
    </div>
  )
}
