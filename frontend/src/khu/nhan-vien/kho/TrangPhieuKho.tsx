import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Drawer, Form, Input, InputNumber, Select, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { type DongNhap, type KhuTon, type LyDoHuy, type TrangThaiDuyet, NHAN_DUYET, NHAN_KHU, NHAN_LY_DO_HUY, kiemTraDong, tonKhu } from './phieuKho'

type Loai = 'huy' | 'xuat-tra'
type TonSp = components['schemas']['TonSanPham']
type TonLo = components['schemas']['TonLo']
type Ncc = components['schemas']['NhaCungCapRa']

const CAU_HINH: Record<Loai, { tieuDe: string; nutLap: string; khoa: string }> = {
  huy: { tieuDe: 'Lập phiếu hủy hàng', nutLap: 'Lập phiếu hủy', khoa: 'phieu-huy' },
  'xuat-tra': { tieuDe: 'Lập phiếu xuất trả nhà cung cấp', nutLap: 'Lập phiếu xuất trả', khoa: 'xuat-tra' },
}

/** Một dòng form: chọn sản phẩm (tìm theo tên), lô, khu và số lượng; tồn của lô hiển thị để tránh nhập quá. */
function DongForm({ dong, doi, xoa }: { dong: DongNhap; doi: (d: DongNhap) => void; xoa: () => void }) {
  const [q, setQ] = useState('')
  const [spId, setSpId] = useState<number | null>(null)
  const sp = useQuery({
    queryKey: ['nhan-vien', 'phieu-kho', 'sp', q],
    enabled: q.trim().length >= 2,
    queryFn: async () => (await api.GET('/api/v1/noi-bo/ton-kho', { params: { query: { q: q.trim(), kich_thuoc: 20 } } })).data?.du_lieu ?? [],
  })
  const lo = useQuery({
    queryKey: ['nhan-vien', 'phieu-kho', 'lo', spId],
    enabled: spId !== null,
    queryFn: async () => (await api.GET('/api/v1/noi-bo/ton-kho/{san_pham_id}/lo', { params: { path: { san_pham_id: spId as number } } })).data ?? [],
  })
  const loChon = (lo.data ?? []).find((l) => l.lo_id === dong.lo_id)
  const toiDa = loChon ? tonKhu(loChon, dong.tu_khu) : undefined
  return (
    <Space wrap align="start" style={{ width: '100%' }}>
      <Select<number>
        showSearch
        filterOption={false}
        placeholder="Tìm sản phẩm"
        style={{ width: 220 }}
        onSearch={setQ}
        onChange={(v) => { setSpId(v); doi({ ...dong, lo_id: null }) }}
        options={(sp.data ?? []).map((t: TonSp) => ({ value: t.san_pham_id, label: `${t.ten} (${t.sku})` }))}
      />
      <Select<number>
        placeholder="Chọn lô"
        style={{ width: 240 }}
        disabled={spId === null}
        value={dong.lo_id ?? undefined}
        onChange={(v) => doi({ ...dong, lo_id: v })}
        options={(lo.data ?? []).map((l: TonLo) => ({ value: l.lo_id, label: `${l.so_lo} · HSD ${dinhDangNgay(l.han_su_dung)}` }))}
      />
      <Select<KhuTon>
        style={{ width: 140 }}
        value={dong.tu_khu}
        onChange={(v) => doi({ ...dong, tu_khu: v })}
        options={(Object.keys(NHAN_KHU) as KhuTon[]).map((k) => ({ value: k, label: NHAN_KHU[k] }))}
      />
      <InputNumber min={1} max={toiDa} precision={0} placeholder="Số lượng" value={dong.so_luong ?? undefined} onChange={(v) => doi({ ...dong, so_luong: v })} />
      {toiDa !== undefined && <span>Tối đa {toiDa}</span>}
      <Button danger type="link" onClick={xoa}>Xóa dòng</Button>
    </Space>
  )
}

function FormLap({ loai, dong }: { loai: Loai; dong: () => void }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [lyDoHuy, setLyDoHuy] = useState<LyDoHuy>('het_han')
  const [moTa, setMoTa] = useState('')
  const [nccId, setNccId] = useState<number | null>(null)
  const [lyDo, setLyDo] = useState('')
  const [cacDong, setCacDong] = useState<DongNhap[]>([{ lo_id: null, tu_khu: 'kho_ban', so_luong: null }])
  const [loi, setLoi] = useState<string | null>(null)
  const [dangGui, setDangGui] = useState(false)
  const ncc = useQuery({
    queryKey: ['nhan-vien', 'phieu-kho', 'ncc'],
    enabled: loai === 'xuat-tra',
    queryFn: async () => (await api.GET('/api/v1/noi-bo/nha-cung-cap', { params: { query: { kich_thuoc: 100 } } })).data?.du_lieu ?? [],
  })
  const gui = async () => {
    const sai = kiemTraDong(cacDong)
    if (sai) return setLoi(sai)
    if (loai === 'xuat-tra' && (nccId === null || !lyDo.trim())) return setLoi('Chọn nhà cung cấp và nhập lý do')
    setLoi(null)
    setDangGui(true)
    const dongGui = cacDong.map((d) => ({ lo_id: d.lo_id as number, tu_khu: d.tu_khu, so_luong: d.so_luong as number }))
    const kq =
      loai === 'huy'
        ? await goi(() => api.POST('/api/v1/noi-bo/phieu-huy', { body: { ly_do: lyDoHuy, mo_ta: moTa.trim() || null, dong: dongGui } }))
        : await goi(() => api.POST('/api/v1/noi-bo/xuat-tra', { body: { nha_cung_cap_id: nccId as number, ly_do: lyDo.trim(), dong: dongGui } }))
    setDangGui(false)
    if (!kq.ok) return setLoi(thongDiepChung(kq.loi))
    void message.success(`Đã lập phiếu ${kq.data.ma_phieu}, chờ Admin duyệt`)
    void queryClient.invalidateQueries({ queryKey: ['nhan-vien', CAU_HINH[loai].khoa] })
    dong()
  }
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      {loai === 'huy' ? (
        <Form layout="vertical">
          <Form.Item label="Lý do hủy">
            <Select<LyDoHuy> value={lyDoHuy} onChange={setLyDoHuy} options={(Object.keys(NHAN_LY_DO_HUY) as LyDoHuy[]).map((k) => ({ value: k, label: NHAN_LY_DO_HUY[k] }))} />
          </Form.Item>
          <Form.Item label="Mô tả"><Input.TextArea rows={2} maxLength={2000} value={moTa} onChange={(e) => setMoTa(e.target.value)} /></Form.Item>
        </Form>
      ) : (
        <Form layout="vertical">
          <Form.Item label="Nhà cung cấp">
            <Select<number> showSearch optionFilterProp="label" value={nccId ?? undefined} onChange={setNccId} placeholder="Chọn nhà cung cấp" options={(ncc.data ?? []).map((n: Ncc) => ({ value: n.id, label: n.ten }))} />
          </Form.Item>
          <Form.Item label="Lý do"><Input.TextArea rows={2} maxLength={1000} value={lyDo} onChange={(e) => setLyDo(e.target.value)} /></Form.Item>
        </Form>
      )}
      {cacDong.map((d, i) => (
        <DongForm key={i} dong={d} doi={(moi) => setCacDong((cu) => cu.map((x, j) => (j === i ? moi : x)))} xoa={() => setCacDong((cu) => cu.filter((_, j) => j !== i))} />
      ))}
      <Button onClick={() => setCacDong((cu) => [...cu, { lo_id: null, tu_khu: 'kho_ban', so_luong: null }])}>Thêm dòng</Button>
      {loi && <Alert type="error" showIcon message={loi} />}
      <Button type="primary" loading={dangGui} onClick={() => void gui()}>{CAU_HINH[loai].nutLap}</Button>
    </Space>
  )
}

type Tom = components['schemas']['PhieuHuyTomTat'] | components['schemas']['PhieuXuatTraTomTat']

function ChiTiet({ loai, id }: { loai: Loai; id: number }) {
  const q = useQuery({
    queryKey: ['nhan-vien', CAU_HINH[loai].khoa, 'ct', id],
    queryFn: async () => {
      const { data } =
        loai === 'huy'
          ? await api.GET('/api/v1/noi-bo/phieu-huy/{phieu_id}', { params: { path: { phieu_id: id } } })
          : await api.GET('/api/v1/noi-bo/xuat-tra/{phieu_id}', { params: { path: { phieu_id: id } } })
      return data
    },
  })
  const p = q.data
  if (!p) return null
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Descriptions column={2} size="small">
        <Descriptions.Item label="Mã phiếu">{p.ma_phieu}</Descriptions.Item>
        <Descriptions.Item label="Trạng thái">{NHAN_DUYET[p.trang_thai_duyet].nhan}</Descriptions.Item>
        <Descriptions.Item label="Người lập">{p.nguoi_lap.ho_ten}</Descriptions.Item>
        <Descriptions.Item label="Người duyệt">{p.nguoi_duyet?.ho_ten ?? '—'}</Descriptions.Item>
        {'nha_cung_cap' in p && <Descriptions.Item label="Nhà cung cấp" span={2}>{p.nha_cung_cap.ten}</Descriptions.Item>}
        <Descriptions.Item label="Lý do" span={2}>{loai === 'huy' ? (NHAN_LY_DO_HUY[p.ly_do as LyDoHuy] ?? p.ly_do) : p.ly_do}</Descriptions.Item>
        {'mo_ta' in p && p.mo_ta && <Descriptions.Item label="Mô tả" span={2}>{p.mo_ta}</Descriptions.Item>}
        {p.ly_do_tu_choi && <Descriptions.Item label="Lý do từ chối" span={2}>{p.ly_do_tu_choi}</Descriptions.Item>}
      </Descriptions>
      <Table
        size="small"
        rowKey={(d) => `${d.lo_id}:${d.tu_khu}`}
        pagination={false}
        dataSource={p.dong}
        columns={[
          { title: 'Sản phẩm', key: 'sp', render: (_, d) => `${d.san_pham.ten} (${d.san_pham.sku})` },
          { title: 'Số lô', dataIndex: 'so_lo', key: 'lo' },
          { title: 'HSD', key: 'hsd', render: (_, d) => dinhDangNgay(d.han_su_dung) },
          { title: 'Khu', key: 'khu', render: (_, d) => NHAN_KHU[d.tu_khu] },
          { title: 'Số lượng', dataIndex: 'so_luong', key: 'sl', align: 'right' },
        ]}
      />
    </Space>
  )
}

/** KHO09, KHO11: danh sách, chi tiết và form lập phiếu hủy / phiếu xuất trả NCC. Tồn chỉ đổi khi Admin duyệt (AD12). */
export default function TrangPhieuKho({ loai }: { loai: Loai }) {
  const cfg = CAU_HINH[loai]
  const [trangThai, setTrangThai] = useState<TrangThaiDuyet | undefined>()
  const [trang, setTrang] = useState(1)
  const [xem, setXem] = useState<number | null>(null)
  const [lap, setLap] = useState(false)
  const ds = useQuery({
    queryKey: ['nhan-vien', cfg.khoa, trangThai, trang],
    queryFn: async () => {
      const query = { trang_thai_duyet: trangThai, trang, kich_thuoc: 20 }
      const { data, error } =
        loai === 'huy' ? await api.GET('/api/v1/noi-bo/phieu-huy', { params: { query } }) : await api.GET('/api/v1/noi-bo/xuat-tra', { params: { query } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
    placeholderData: (truoc) => truoc,
  })
  const cot: ColumnsType<Tom> = [
    { title: 'Mã phiếu', key: 'ma', render: (_, p) => <Button type="link" style={{ padding: 0 }} onClick={() => setXem(p.id)}>{p.ma_phieu}</Button> },
    ...(loai === 'xuat-tra' ? ([{ title: 'Nhà cung cấp', key: 'ncc', render: (_, p) => ('nha_cung_cap' in p ? p.nha_cung_cap.ten : '') }] as ColumnsType<Tom>) : []),
    { title: 'Lý do', key: 'ld', ellipsis: true, render: (_, p) => (loai === 'huy' ? (NHAN_LY_DO_HUY[p.ly_do as LyDoHuy] ?? p.ly_do) : p.ly_do) },
    { title: 'Số dòng', dataIndex: 'so_dong', key: 'sd', align: 'right' },
    { title: 'Trạng thái', key: 'tt', render: (_, p) => <Tag color={NHAN_DUYET[p.trang_thai_duyet].mau}>{NHAN_DUYET[p.trang_thai_duyet].nhan}</Tag> },
    { title: 'Ngày lập', key: 'ngay', render: (_, p) => dinhDangNgay(p.created_at, 'ngayGio') },
  ]
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space>
        <Select allowClear placeholder="Trạng thái" style={{ width: 180 }} value={trangThai} onChange={(v) => { setTrangThai(v); setTrang(1) }} options={(Object.keys(NHAN_DUYET) as TrangThaiDuyet[]).map((k) => ({ value: k, label: NHAN_DUYET[k].nhan }))} />
        <Button type="primary" onClick={() => setLap(true)}>{cfg.nutLap}</Button>
      </Space>
      {ds.isError && <Alert type="error" showIcon message="Không tải được danh sách phiếu" />}
      <Table<Tom> rowKey="id" columns={cot} dataSource={ds.data?.du_lieu ?? []} loading={ds.isLoading} pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }} />
      <Drawer title={cfg.tieuDe} open={lap} onClose={() => setLap(false)} size="large" destroyOnHidden>
        <FormLap loai={loai} dong={() => setLap(false)} />
      </Drawer>
      <Drawer title="Chi tiết phiếu" open={xem !== null} onClose={() => setXem(null)} size="large" destroyOnHidden>
        {xem !== null && <ChiTiet loai={loai} id={xem} />}
      </Drawer>
    </Space>
  )
}
