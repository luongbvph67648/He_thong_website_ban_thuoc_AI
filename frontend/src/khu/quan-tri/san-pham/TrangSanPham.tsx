import { PlusOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Input, Select, Space, Table, Tag, TreeSelect, Typography } from 'antd'
import type { ColumnsType, SorterResult } from 'antd/es/table/interface'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { NhanTrangThai } from '../../../components/NhanTrangThai'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangTien } from '../../../lib/dinhDang'
import { KHOA_QUERY_SAN_PHAM, TUY_CHON_KINH_DOANH, TUY_CHON_LOAI, type SanPhamTomTat } from './sanPham'
import { useCayDanhMuc } from './useCayDanhMuc'

const KICH_THUOC = 20
/** Trường backend cho sắp xếp (spec 06 mục 3.11); giá trị khác trên URL bị bỏ qua. */
const TRUONG_SAP_XEP = ['created_at', 'ten', 'sku'] as const
type TruongSapXep = (typeof TRUONG_SAP_XEP)[number]

function docSapXep(gia: string | null): { truong: TruongSapXep; giam: boolean } | null {
  const truong = gia?.replace(/^-/, '')
  return TRUONG_SAP_XEP.find((t) => t === truong) ? { truong: truong as TruongSapXep, giam: gia!.startsWith('-') } : null
}

const IDS_HOP_LE = /^[1-9]\d{0,9}$/

/** Danh sách sản phẩm (AD04): tìm theo tên/SKU, lọc loại, danh mục, trạng thái; mọi bộ lọc nằm trên URL. */
export default function TrangSanPham() {
  const [tham, datTham] = useSearchParams()
  // Trang nằm dưới `/quan-tri`: liên kết phải giữ tiền tố của khu, nên dựng từ đường dẫn hiện tại chứ không viết cứng.
  const gocTrang = useLocation().pathname.replace(/\/+$/, '')
  const q = tham.get('q') ?? ''
  const loai = TUY_CHON_LOAI.find((o) => o.value === tham.get('loai'))?.value
  const trangThai = TUY_CHON_KINH_DOANH.find((o) => o.value === tham.get('trang_thai'))?.value
  const danhMucTho = tham.get('danh_muc_id')
  const danhMucId = danhMucTho && IDS_HOP_LE.test(danhMucTho) ? Number(danhMucTho) : undefined
  const sapXepTho = tham.get('sap_xep')
  const sapXep = docSapXep(sapXepTho)
  const trang = Math.max(1, Number(tham.get('trang')) || 1)
  const sapXepGui = sapXep ? `${sapXep.giam ? '-' : ''}${sapXep.truong}` : undefined

  const doiThamSo = (thayDoi: Record<string, string | undefined>) => {
    const moi = new URLSearchParams(tham)
    for (const [k, v] of Object.entries({ trang: undefined, ...thayDoi })) {
      if (v) moi.set(k, v)
      else moi.delete(k)
    }
    datTham(moi, { replace: true })
  }

  const { tuyChon: tuyChonDanhMuc } = useCayDanhMuc()

  const danhSach = useQuery({
    queryKey: [...KHOA_QUERY_SAN_PHAM, 'danh-sach', { q, loai, trangThai, danhMucId, sapXepGui, trang }],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/san-pham', {
        params: { query: { q: q || undefined, loai, trang_thai: trangThai, danh_muc_id: danhMucId, sap_xep: sapXepGui, trang, kich_thuoc: KICH_THUOC } },
      })
      if (error) throw error
      return data
    },
  })

  const thuTuCot = (truong: TruongSapXep) => (sapXep?.truong === truong ? (sapXep.giam ? ('descend' as const) : ('ascend' as const)) : null)

  const cot: ColumnsType<SanPhamTomTat> = [
    {
      title: 'Ảnh',
      key: 'anh',
      width: 72,
      render: (_, s) =>
        s.anh_chinh_url ? <img src={s.anh_chinh_url} alt={`Ảnh ${s.ten}`} style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 4 }} /> : <span aria-hidden>—</span>,
    },
    { title: 'SKU', key: 'sku', dataIndex: 'sku', sorter: true, sortOrder: thuTuCot('sku') },
    {
      title: 'Tên sản phẩm',
      key: 'ten',
      sorter: true,
      sortOrder: thuTuCot('ten'),
      render: (_, s) => (
        <Space size={4} wrap>
          <Link to={`${gocTrang}/${s.id}`}>{s.ten}</Link>
          {s.la_noi_bat && <Tag color="gold">Nổi bật</Tag>}
        </Space>
      ),
    },
    { title: 'Loại', key: 'loai', render: (_, s) => <NhanTrangThai loai="loai_san_pham" giaTri={s.loai_san_pham} /> },
    { title: 'Danh mục', key: 'danh_muc', dataIndex: 'ten_danh_muc' },
    { title: 'Thương hiệu', key: 'thuong_hieu', render: (_, s) => s.ten_thuong_hieu ?? '—' },
    { title: 'Giá bán', key: 'gia', align: 'right', render: (_, s) => dinhDangTien(s.gia_mac_dinh) },
    { title: 'Trạng thái', key: 'trang_thai', render: (_, s) => <NhanTrangThai loai="kinh_doanh" giaTri={s.trang_thai} /> },
  ]

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }} align="start" wrap>
        <Typography.Title level={3} style={{ margin: 0 }}>
          Sản phẩm
        </Typography.Title>
        <YeuCauQuyen ma="product.commercial.manage" kieu="nut">
          <Link to={`${gocTrang}/moi`}>
            <Button type="primary" icon={<PlusOutlined />}>
              Thêm sản phẩm
            </Button>
          </Link>
        </YeuCauQuyen>
      </Space>

      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search
          key={q}
          defaultValue={q}
          allowClear
          placeholder="Tìm theo tên hoặc SKU"
          style={{ width: 300 }}
          onSearch={(v) => doiThamSo({ q: v.trim() || undefined })}
        />
        <Select allowClear placeholder="Loại sản phẩm" style={{ width: 200 }} value={loai} options={TUY_CHON_LOAI} onChange={(v: string | undefined) => doiThamSo({ loai: v })} aria-label="Lọc theo loại" />
        <TreeSelect
          allowClear
          showSearch
          treeNodeFilterProp="title"
          treeDefaultExpandAll
          placeholder="Danh mục (gồm cả danh mục con)"
          style={{ width: 260 }}
          value={danhMucId}
          treeData={tuyChonDanhMuc}
          onChange={(v: number | undefined) => doiThamSo({ danh_muc_id: v === undefined ? undefined : String(v) })}
          aria-label="Lọc theo danh mục"
        />
        <Select allowClear placeholder="Trạng thái" style={{ width: 180 }} value={trangThai} options={TUY_CHON_KINH_DOANH} onChange={(v: string | undefined) => doiThamSo({ trang_thai: v })} aria-label="Lọc theo trạng thái" />
      </Space>

      {danhSach.isError && <Alert type="error" showIcon title="Không tải được danh sách sản phẩm" style={{ marginBottom: 16 }} />}
      <Table<SanPhamTomTat>
        rowKey="id"
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
        onChange={(_, __, sorter, extra) => {
          // antd gọi `onChange` này cho cả lần bấm trang (sau `pagination.onChange`); xử lý ở đây sẽ xóa `trang` vừa đặt.
          if (extra.action !== 'sort') return
          const s = Array.isArray(sorter) ? sorter[0] : (sorter as SorterResult<SanPhamTomTat>)
          const truong = String(s?.columnKey ?? '')
          doiThamSo({ sap_xep: s?.order && TRUONG_SAP_XEP.some((t) => t === truong) ? `${s.order === 'descend' ? '-' : ''}${truong}` : undefined })
        }}
        locale={{ emptyText: 'Không có sản phẩm phù hợp', triggerAsc: 'Bấm để sắp xếp tăng dần', triggerDesc: 'Bấm để sắp xếp giảm dần', cancelSort: 'Bấm để bỏ sắp xếp' }}
      />
    </div>
  )
}
