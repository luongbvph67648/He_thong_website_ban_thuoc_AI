import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Drawer, Input, InputNumber, Popconfirm, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'
import { chenhLech, locDong } from './kiemKe'

type Tom = components['schemas']['KiemKeTomTat']
type Dong = components['schemas']['DongKiemKe']
const KHOA = ['nhan-vien', 'kiem-ke'] as const

/** Nhập số lượng thực tế theo lô, chốt rồi lập phiếu điều chỉnh từ các dòng lệch. */
function ChiTiet({ id, coGhi, dong }: { id: number; coGhi: boolean; dong: () => void }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [loc, setLoc] = useState('')
  const [chiLech, setChiLech] = useState(false)
  const [nhap, setNhap] = useState<Record<number, number | null>>({})
  const [loi, setLoi] = useState<string | null>(null)
  const q = useQuery({
    queryKey: [...KHOA, 'ct', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/kiem-ke/{phieu_id}', { params: { path: { phieu_id: id } } })
      if (error || !data) throw error ?? new Error('Không tải được phiếu')
      return data
    },
    staleTime: Infinity,
    gcTime: 0,
  })
  const p = q.data
  const dangKiem = p?.trang_thai === 'dang_kiem'
  const lamMoi = () => void queryClient.invalidateQueries({ queryKey: KHOA })

  const luu = async () => {
    const dongGui = Object.entries(nhap).filter(([, v]) => v !== null && v !== undefined).map(([lo, v]) => ({ lo_id: Number(lo), so_luong_thuc_te: v as number }))
    if (!dongGui.length) return
    setLoi(null)
    const kq = await goi(() => api.PUT('/api/v1/noi-bo/kiem-ke/{phieu_id}/so-luong', { params: { path: { phieu_id: id } }, body: { dong: dongGui.slice(0, 500) } }))
    if (!kq.ok) return setLoi(thongDiepChung(kq.loi))
    setNhap({})
    void queryClient.setQueryData([...KHOA, 'ct', id], kq.data)
    void message.success(`Đã lưu ${dongGui.length} dòng`)
  }
  const chot = async () => {
    await luu()
    const kq = await goi(() => api.POST('/api/v1/noi-bo/kiem-ke/{phieu_id}/chot', { params: { path: { phieu_id: id } } }))
    if (!kq.ok) return setLoi(thongDiepChung(kq.loi))
    void queryClient.setQueryData([...KHOA, 'ct', id], kq.data)
    void message.success('Đã chốt kiểm kê')
    lamMoi()
  }
  const lapDieuChinh = async () => {
    const kq = await goi(() => api.POST('/api/v1/noi-bo/dieu-chinh', { body: { ly_do: `Điều chỉnh theo kiểm kê ${p?.ma_phieu}`, phieu_kiem_ke_id: id } }))
    if (!kq.ok) return setLoi(thongDiepChung(kq.loi))
    void message.success(`Đã lập phiếu điều chỉnh ${kq.data.ma_phieu}, chờ Admin duyệt`)
    dong()
  }
  const xoa = async () => {
    const kq = await goi(() => api.DELETE('/api/v1/noi-bo/kiem-ke/{phieu_id}', { params: { path: { phieu_id: id } } }))
    if (!kq.ok) return setLoi(thongDiepChung(kq.loi))
    lamMoi()
    dong()
  }

  const cot: ColumnsType<Dong> = [
    { title: 'Sản phẩm', key: 'sp', render: (_, d) => `${d.san_pham.ten} (${d.san_pham.sku})` },
    { title: 'Số lô', dataIndex: 'so_lo', key: 'lo', width: 120 },
    { title: 'HSD', key: 'hsd', width: 110, render: (_, d) => dinhDangNgay(d.han_su_dung) },
    { title: 'Sổ sách', dataIndex: 'so_luong_so_sach', key: 'ss', width: 90, align: 'right' },
    {
      title: 'Thực tế',
      key: 'tt',
      width: 120,
      render: (_, d) =>
        dangKiem && coGhi ? (
          <InputNumber aria-label={`Thực tế ${d.so_lo}`} precision={0} value={nhap[d.lo_id] ?? d.so_luong_thuc_te} onChange={(v) => setNhap((n) => ({ ...n, [d.lo_id]: v }))} style={{ width: 100 }} />
        ) : (
          d.so_luong_thuc_te
        ),
    },
    {
      title: 'Chênh lệch',
      key: 'cl',
      width: 100,
      align: 'right',
      render: (_, d) => {
        const c = chenhLech(d.so_luong_so_sach, nhap[d.lo_id] ?? d.so_luong_thuc_te)
        return c === null ? '' : <Tag color={c === 0 ? 'default' : c < 0 ? 'red' : 'blue'}>{c > 0 ? `+${c}` : c}</Tag>
      },
    },
  ]
  const hienThi = locDong(p?.dong ?? [], loc, chiLech, nhap)
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      {loi && <Alert type="error" showIcon message={loi} />}
      {p && (
        <Typography.Text>
          {p.ma_phieu} · {p.danh_muc?.ten ?? 'Toàn kho'} · {dangKiem ? 'Đang kiểm' : `Đã chốt ${dinhDangNgay(p.chot_luc, 'ngayGio')}`} · {p.so_dong_lech} dòng lệch
        </Typography.Text>
      )}
      <Space wrap>
        <Input.Search allowClear placeholder="Tìm sản phẩm hoặc số lô" style={{ width: 260 }} onSearch={setLoc} />
        <label>
          <input type="checkbox" checked={chiLech} onChange={(e) => setChiLech(e.target.checked)} /> Chỉ dòng lệch
        </label>
      </Space>
      <Table<Dong> size="small" rowKey="lo_id" columns={cot} dataSource={hienThi} loading={q.isLoading} pagination={{ pageSize: 50, showSizeChanger: false }} />
      {coGhi && (
        <Space>
          {dangKiem && (
            <>
              <Button onClick={() => void luu()}>Lưu số đã nhập</Button>
              <Popconfirm title="Chốt kiểm kê? Sau khi chốt không sửa được số thực tế." okText="Chốt" cancelText="Hủy" onConfirm={() => void chot()}>
                <Button type="primary">Chốt kiểm kê</Button>
              </Popconfirm>
              <Popconfirm title="Xóa phiếu đang kiểm?" okText="Xóa" cancelText="Hủy" onConfirm={() => void xoa()}>
                <Button danger>Xóa phiếu</Button>
              </Popconfirm>
            </>
          )}
          {p?.trang_thai === 'da_chot' && p.so_dong_lech > 0 && (
            <Button type="primary" onClick={() => void lapDieuChinh()}>
              Lập phiếu điều chỉnh từ các dòng lệch
            </Button>
          )}
        </Space>
      )}
    </Space>
  )
}

/** KHO07: danh sách phiếu kiểm kê, lập phiếu (toàn kho hoặc theo danh mục), mở để nhập số thực tế. */
export default function TrangKiemKe() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const coGhi = coQuyen(usePhien((s) => s.quyen), 'stocktake.manage')
  const [trang, setTrang] = useState(1)
  const [mo, setMo] = useState<number | null>(null)
  const [danhMuc, setDanhMuc] = useState<number | undefined>()
  const ds = useQuery({
    queryKey: [...KHOA, 'ds', trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/kiem-ke', { params: { query: { trang, kich_thuoc: 20 } } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
    placeholderData: (truoc) => truoc,
  })
  const dm = useQuery({
    queryKey: ['nhan-vien', 'kiem-ke', 'danh-muc'],
    queryFn: async () => (await api.GET('/api/v1/danh-muc')).data ?? [],
  })
  const lapPhieu = async () => {
    const kq = await goi(() => api.POST('/api/v1/noi-bo/kiem-ke', { body: { danh_muc_id: danhMuc ?? null } }))
    if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
    void queryClient.invalidateQueries({ queryKey: KHOA })
    setMo(kq.data.id)
  }
  const phang = (nut: components['schemas']['DanhMucCongKhai'][], cap = 0): { value: number; label: string }[] =>
    nut.flatMap((n) => [{ value: n.id, label: `${'— '.repeat(cap)}${n.ten}` }, ...phang(n.con ?? [], cap + 1)])
  const cot: ColumnsType<Tom> = [
    { title: 'Mã phiếu', key: 'ma', render: (_, p) => <Button type="link" style={{ padding: 0 }} onClick={() => setMo(p.id)}>{p.ma_phieu}</Button> },
    { title: 'Phạm vi', key: 'pv', render: (_, p) => p.danh_muc?.ten ?? 'Toàn kho' },
    { title: 'Trạng thái', key: 'tt', render: (_, p) => <Tag color={p.trang_thai === 'da_chot' ? 'green' : 'gold'}>{p.trang_thai === 'da_chot' ? 'Đã chốt' : 'Đang kiểm'}</Tag> },
    { title: 'Số dòng', dataIndex: 'so_dong', key: 'sd', align: 'right' },
    { title: 'Dòng lệch', dataIndex: 'so_dong_lech', key: 'sl', align: 'right' },
    { title: 'Người lập', key: 'nv', render: (_, p) => p.nhan_vien.ho_ten },
    { title: 'Ngày chụp tồn', key: 'ngay', render: (_, p) => dinhDangNgay(p.thoi_diem_chup_ton, 'ngayGio') },
  ]
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      {coGhi && (
        <Space wrap>
          <Select allowClear showSearch optionFilterProp="label" placeholder="Toàn kho (hoặc chọn danh mục)" style={{ width: 300 }} value={danhMuc} onChange={setDanhMuc} options={phang(dm.data ?? [])} />
          <Button type="primary" onClick={() => void lapPhieu()}>
            Lập phiếu kiểm kê
          </Button>
        </Space>
      )}
      {ds.isError && <Alert type="error" showIcon message="Không tải được danh sách phiếu kiểm kê" />}
      <Table<Tom> rowKey="id" columns={cot} dataSource={ds.data?.du_lieu ?? []} loading={ds.isLoading} pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }} />
      <Drawer title="Phiếu kiểm kê" open={mo !== null} onClose={() => { setMo(null); void queryClient.invalidateQueries({ queryKey: KHOA }) }} size="large" destroyOnHidden>
        {mo !== null && <ChiTiet id={mo} coGhi={coGhi} dong={() => setMo(null)} />}
      </Drawer>
    </Space>
  )
}
