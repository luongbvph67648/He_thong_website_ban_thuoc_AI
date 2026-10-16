import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Drawer, Input, Modal, Popconfirm, Select, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'
import { type LoaiPhieu, type TrangThaiDuyet, NHAN_DUYET, NHAN_KHU, NHAN_LOAI } from '../../nhan-vien/kho/phieuKho'

type Dong = components['schemas']['PhieuChoDuyet']
const KHOA = ['quan-tri', 'duyet-phieu'] as const
type ChiTietPhieu = components['schemas']['PhieuHuyChiTiet'] | components['schemas']['PhieuXuatTraChiTiet'] | components['schemas']['DieuChinhChiTiet']

/** Dòng chi tiết thống nhất cho cả ba loại phiếu. */
function dongHienThi(p: ChiTietPhieu) {
  return p.dong.map((d) => ({
    khoa: `${d.lo_id}:${'tu_khu' in d ? d.tu_khu : 'dc'}`,
    sanPham: `${d.san_pham.ten} (${d.san_pham.sku})`,
    soLo: d.so_lo,
    khu: 'tu_khu' in d ? NHAN_KHU[d.tu_khu] : 'Khu bán',
    soLuong: 'so_luong_thay_doi' in d ? (d.so_luong_thay_doi > 0 ? `+${d.so_luong_thay_doi}` : `${d.so_luong_thay_doi}`) : `-${d.so_luong}`,
  }))
}

function ChiTiet({ loai, id, dong }: { loai: LoaiPhieu; id: number; dong: () => void }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const coGhi = coQuyen(usePhien((s) => s.quyen), 'stock_doc.approve', 'day_du')
  const [tuChoi, setTuChoi] = useState(false)
  const [lyDo, setLyDo] = useState('')
  const [loi, setLoi] = useState<string | null>(null)
  const q = useQuery({
    queryKey: [...KHOA, 'ct', loai, id],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/duyet-phieu/{loai}/{phieu_id}', { params: { path: { loai, phieu_id: id } } })
      if (error || !data) throw error ?? new Error('Không tải được phiếu')
      return data as ChiTietPhieu
    },
    gcTime: 0,
  })
  const p = q.data
  const xong = (thongBao: string) => {
    void message.success(thongBao)
    void queryClient.invalidateQueries({ queryKey: KHOA })
    dong()
  }
  const duyet = async () => {
    setLoi(null)
    const kq = await goi(() => api.POST('/api/v1/noi-bo/duyet-phieu/{loai}/{phieu_id}/duyet', { params: { path: { loai, phieu_id: id } } }))
    if (!kq.ok) return setLoi(thongDiepChung(kq.loi))
    xong('Đã duyệt phiếu, tồn kho đã cập nhật')
  }
  const tuChoiPhieu = async () => {
    if (!lyDo.trim()) return setLoi('Cần nhập lý do từ chối')
    setLoi(null)
    const kq = await goi(() => api.POST('/api/v1/noi-bo/duyet-phieu/{loai}/{phieu_id}/tu-choi', { params: { path: { loai, phieu_id: id } }, body: { ly_do: lyDo.trim() } }))
    if (!kq.ok) return setLoi(thongDiepChung(kq.loi))
    setTuChoi(false)
    xong('Đã từ chối phiếu')
  }
  if (!p) return null
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Descriptions column={2} size="small">
        <Descriptions.Item label="Mã phiếu">{p.ma_phieu}</Descriptions.Item>
        <Descriptions.Item label="Loại">{NHAN_LOAI[loai]}</Descriptions.Item>
        <Descriptions.Item label="Trạng thái">{NHAN_DUYET[p.trang_thai_duyet].nhan}</Descriptions.Item>
        <Descriptions.Item label="Người lập">{p.nguoi_lap.ho_ten}</Descriptions.Item>
        {'nha_cung_cap' in p && <Descriptions.Item label="Nhà cung cấp" span={2}>{p.nha_cung_cap.ten}</Descriptions.Item>}
        <Descriptions.Item label="Lý do" span={2}>{p.ly_do}</Descriptions.Item>
        {p.ly_do_tu_choi && <Descriptions.Item label="Lý do từ chối" span={2}>{p.ly_do_tu_choi}</Descriptions.Item>}
      </Descriptions>
      <Table
        size="small"
        rowKey="khoa"
        pagination={false}
        dataSource={dongHienThi(p)}
        columns={[
          { title: 'Sản phẩm', dataIndex: 'sanPham', key: 'sp' },
          { title: 'Số lô', dataIndex: 'soLo', key: 'lo' },
          { title: 'Khu', dataIndex: 'khu', key: 'khu' },
          { title: 'Thay đổi tồn', dataIndex: 'soLuong', key: 'sl', align: 'right' },
        ]}
      />
      {loi && <Alert type="error" showIcon message={loi} />}
      {coGhi && p.trang_thai_duyet === 'cho_duyet' && (
        <Space>
          <Popconfirm title="Duyệt phiếu và cập nhật tồn kho?" okText="Duyệt" cancelText="Hủy" onConfirm={() => void duyet()}>
            <Button type="primary">Duyệt</Button>
          </Popconfirm>
          <Button danger onClick={() => setTuChoi(true)}>Từ chối</Button>
        </Space>
      )}
      <Modal title="Từ chối phiếu" open={tuChoi} okText="Từ chối" cancelText="Hủy" okButtonProps={{ danger: true }} onOk={() => void tuChoiPhieu()} onCancel={() => setTuChoi(false)} destroyOnHidden>
        <Input.TextArea rows={3} maxLength={1000} placeholder="Lý do từ chối (bắt buộc)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
      </Modal>
    </Space>
  )
}

/** AD12: danh sách phiếu điều chỉnh, hủy, xuất trả chờ duyệt (gộp ba loại). Người lập không tự duyệt (backend chặn). */
export default function TrangDuyetPhieu() {
  const [trangThai, setTrangThai] = useState<TrangThaiDuyet | undefined>('cho_duyet')
  const [loai, setLoai] = useState<LoaiPhieu | undefined>()
  const [trang, setTrang] = useState(1)
  const [xem, setXem] = useState<{ loai: LoaiPhieu; id: number } | null>(null)
  const ds = useQuery({
    queryKey: [...KHOA, trangThai, loai, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/duyet-phieu', { params: { query: { loai, trang_thai_duyet: trangThai, trang, kich_thuoc: 20 } } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
    placeholderData: (truoc) => truoc,
  })
  const cot: ColumnsType<Dong> = [
    { title: 'Mã phiếu', key: 'ma', render: (_, p) => <Button type="link" style={{ padding: 0 }} onClick={() => setXem({ loai: p.loai, id: p.id })}>{p.ma_phieu}</Button> },
    { title: 'Loại', key: 'loai', render: (_, p) => NHAN_LOAI[p.loai] },
    { title: 'Lý do', dataIndex: 'ly_do', key: 'ld', ellipsis: true },
    { title: 'Người lập', key: 'nl', render: (_, p) => p.nguoi_lap.ho_ten },
    { title: 'Số dòng', dataIndex: 'so_dong', key: 'sd', align: 'right' },
    { title: 'Trạng thái', key: 'tt', render: (_, p) => <Tag color={NHAN_DUYET[p.trang_thai_duyet].mau}>{NHAN_DUYET[p.trang_thai_duyet].nhan}</Tag> },
    { title: 'Ngày lập', key: 'ngay', render: (_, p) => dinhDangNgay(p.created_at, 'ngayGio') },
  ]
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space>
        <Select allowClear placeholder="Trạng thái" style={{ width: 180 }} value={trangThai} onChange={(v) => { setTrangThai(v); setTrang(1) }} options={(Object.keys(NHAN_DUYET) as TrangThaiDuyet[]).map((k) => ({ value: k, label: NHAN_DUYET[k].nhan }))} />
        <Select allowClear placeholder="Loại phiếu" style={{ width: 180 }} value={loai} onChange={(v) => { setLoai(v); setTrang(1) }} options={(Object.keys(NHAN_LOAI) as LoaiPhieu[]).map((k) => ({ value: k, label: NHAN_LOAI[k] }))} />
      </Space>
      {ds.isError && <Alert type="error" showIcon message="Không tải được danh sách phiếu" />}
      <Table<Dong> rowKey={(p) => `${p.loai}:${p.id}`} columns={cot} dataSource={ds.data?.du_lieu ?? []} loading={ds.isLoading} pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }} />
      <Drawer title="Duyệt phiếu kho" open={xem !== null} onClose={() => setXem(null)} size="large" destroyOnHidden>
        {xem && <ChiTiet loai={xem.loai} id={xem.id} dong={() => setXem(null)} />}
      </Drawer>
    </Space>
  )
}
