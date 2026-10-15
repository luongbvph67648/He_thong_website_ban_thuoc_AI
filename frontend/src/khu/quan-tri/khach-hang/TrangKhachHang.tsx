import { useQuery } from '@tanstack/react-query'
import { Alert, Input, Select, Space, Table, Typography } from 'antd'
import type { ColumnsType, SorterResult } from 'antd/es/table/interface'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { KHOA_QUERY_KHACH } from './khach'
import { NhanTaiKhoan } from './NhanTaiKhoan'
import { NutKhoaMoKhoaKhach } from './NutKhoaMoKhoaKhach'

type KhachHang = components['schemas']['KhachHangTomTat']
type TrangThai = 'hoat_dong' | 'bi_khoa'

const KICH_THUOC = 20
/** Trường backend cho sắp xếp (spec 06 mục 3.6); giá trị khác trên URL bị bỏ qua. */
const TRUONG_SAP_XEP = ['created_at', 'ho_ten', 'email', 'so_dien_thoai'] as const
type TruongSapXep = (typeof TRUONG_SAP_XEP)[number]

function docSapXep(gia: string | null): { truong: TruongSapXep; giam: boolean } | null {
  const truong = gia?.replace(/^-/, '')
  return TRUONG_SAP_XEP.find((t) => t === truong) ? { truong: truong as TruongSapXep, giam: gia!.startsWith('-') } : null
}

/** Quản lý khách hàng (AD02): tìm theo tên/email/số điện thoại, lọc, sắp xếp, khóa/mở khóa. Không có hồ sơ sức khỏe. */
export default function TrangKhachHang() {
  const [tham, datTham] = useSearchParams()
  // Trang nằm dưới `/quan-tri`: liên kết phải giữ tiền tố của khu, nên dựng từ đường dẫn hiện tại chứ không viết cứng.
  const gocTrang = useLocation().pathname.replace(/\/+$/, '')
  const q = tham.get('q') ?? ''
  const trangThaiTho = tham.get('trang_thai')
  const trangThai: TrangThai | undefined = trangThaiTho === 'hoat_dong' || trangThaiTho === 'bi_khoa' ? trangThaiTho : undefined
  const sapXepTho = tham.get('sap_xep')
  const sapXep = docSapXep(sapXepTho)
  const trang = Math.max(1, Number(tham.get('trang')) || 1)

  const doiThamSo = (thayDoi: Record<string, string | undefined>) => {
    const moi = new URLSearchParams(tham)
    for (const [k, v] of Object.entries({ trang: undefined, ...thayDoi })) {
      if (v) moi.set(k, v)
      else moi.delete(k)
    }
    datTham(moi, { replace: true })
  }

  const sapXepGui = sapXep ? `${sapXep.giam ? '-' : ''}${sapXep.truong}` : undefined
  const danhSach = useQuery({
    queryKey: [...KHOA_QUERY_KHACH, 'danh-sach', { q, trangThai, sapXepGui, trang }],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/khach-hang', {
        params: { query: { q: q || undefined, trang_thai: trangThai, sap_xep: sapXepGui, trang, kich_thuoc: KICH_THUOC } },
      })
      if (error) throw error
      return data
    },
  })

  const thuTuCot = (truong: TruongSapXep) => (sapXep?.truong === truong ? (sapXep.giam ? ('descend' as const) : ('ascend' as const)) : null)

  const cot: ColumnsType<KhachHang> = [
    {
      title: 'Họ và tên',
      key: 'ho_ten',
      sorter: true,
      sortOrder: thuTuCot('ho_ten'),
      render: (_, k) => <Link to={`${gocTrang}/${k.id}`}>{k.ho_ten}</Link>,
    },
    { title: 'Số điện thoại', key: 'so_dien_thoai', dataIndex: 'so_dien_thoai', sorter: true, sortOrder: thuTuCot('so_dien_thoai') },
    { title: 'Email', key: 'email', sorter: true, sortOrder: thuTuCot('email'), render: (_, k) => k.email ?? '—' },
    { title: 'Ngày đăng ký', key: 'created_at', sorter: true, sortOrder: thuTuCot('created_at'), render: (_, k) => dinhDangNgay(k.created_at) },
    { title: 'Trạng thái', key: 'trang_thai', render: (_, k) => <NhanTaiKhoan khach={k} /> },
    { title: 'Thao tác', key: 'thao_tac', render: (_, k) => <NutKhoaMoKhoaKhach khach={k} /> },
  ]

  return (
    <div>
      <Typography.Title level={3}>Khách hàng</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search
          key={q}
          defaultValue={q}
          allowClear
          placeholder="Tìm theo tên, email, số điện thoại"
          style={{ width: 340 }}
          onSearch={(v) => doiThamSo({ q: v.trim() || undefined })}
        />
        <Select
          allowClear
          placeholder="Trạng thái"
          style={{ width: 160 }}
          value={trangThai}
          options={[
            { value: 'hoat_dong', label: 'Hoạt động' },
            { value: 'bi_khoa', label: 'Bị khóa' },
          ]}
          onChange={(v: string | undefined) => doiThamSo({ trang_thai: v })}
          aria-label="Lọc theo trạng thái"
        />
      </Space>

      {danhSach.isError && <Alert type="error" showIcon title="Không tải được danh sách khách hàng" style={{ marginBottom: 16 }} />}
      <Table<KhachHang>
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
        onChange={(_, __, sorter) => {
          const s = Array.isArray(sorter) ? sorter[0] : (sorter as SorterResult<KhachHang>)
          const truong = String(s?.columnKey ?? '')
          doiThamSo({ sap_xep: s?.order && TRUONG_SAP_XEP.some((t) => t === truong) ? `${s.order === 'descend' ? '-' : ''}${truong}` : undefined })
        }}
        locale={{ emptyText: 'Không có khách hàng phù hợp', triggerAsc: 'Bấm để sắp xếp tăng dần', triggerDesc: 'Bấm để sắp xếp giảm dần', cancelSort: 'Bấm để bỏ sắp xếp' }}
      />
    </div>
  )
}
