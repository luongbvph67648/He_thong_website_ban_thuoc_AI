import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, DatePicker, Form, Input, InputNumber, Modal, Popconfirm, Radio, Select, Space, Switch, Table, Tag, TreeSelect, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import type { components } from '../../../api/schema'
import dayjs from '../../../lib/dayjs'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'
import { type GiaTriForm, type KhuyenMaiChiTiet, type KhuyenMaiTomTat, type TrangThaiHieuLuc, KHOA_KHUYEN_MAI, NHAN_TRANG_THAI, guiTuForm, moTaMucGiam } from './khuyenMai'

type Nut = components['schemas']['DanhMucNut']
interface NutChon {
  value: number
  title: string
  children: NutChon[]
}
const chuyenCay = (ds: Nut[]): NutChon[] => ds.map((n) => ({ value: n.id, title: n.ten, children: chuyenCay(n.con) }))

function MaGiamGia({ id, ghi }: { id: number; ghi: boolean }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [soLuong, setSoLuong] = useState(1)
  const [maRieng, setMaRieng] = useState('')
  const ct = useQuery({
    queryKey: [...KHOA_KHUYEN_MAI, 'ct', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/khuyen-mai/{km_id}', { params: { path: { km_id: id } } })
      if (error || !data) throw error ?? new Error('Không tải được khuyến mãi')
      return data
    },
  })
  const lamMoi = async () => {
    await queryClient.invalidateQueries({ queryKey: KHOA_KHUYEN_MAI })
  }
  async function sinh(body: { ma?: string; so_luong: number }) {
    const kq = await goi(() => api.POST('/api/v1/noi-bo/khuyen-mai/{km_id}/ma', { params: { path: { km_id: id } }, body }))
    if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
    setMaRieng('')
    void message.success(`Đã tạo ${kq.data.length} mã`)
    await lamMoi()
  }
  async function xoa(maId: number) {
    const kq = await goi(() => api.DELETE('/api/v1/noi-bo/khuyen-mai/{km_id}/ma/{ma_id}', { params: { path: { km_id: id, ma_id: maId } } }))
    if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
    await lamMoi()
  }
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      {ghi && (
        <Space wrap>
          <InputNumber aria-label="Số mã cần sinh" min={1} max={100} precision={0} value={soLuong} onChange={(v) => setSoLuong(v ?? 1)} />
          <Button onClick={() => void sinh({ so_luong: soLuong })}>Sinh mã ngẫu nhiên</Button>
          <Input aria-label="Mã tự đặt" placeholder="Mã tự đặt, ví dụ FREESHIP" style={{ width: 220 }} maxLength={30} value={maRieng} onChange={(e) => setMaRieng(e.target.value)} />
          <Button disabled={maRieng.trim().length < 4} onClick={() => void sinh({ ma: maRieng.trim(), so_luong: 1 })}>Thêm mã</Button>
        </Space>
      )}
      <Table
        size="small"
        rowKey="id"
        pagination={false}
        loading={ct.isLoading}
        dataSource={ct.data?.ma_giam_gia ?? []}
        locale={{ emptyText: 'Chưa có mã nào' }}
        columns={[
          { title: 'Mã', dataIndex: 'ma', key: 'ma', render: (v: string) => <Typography.Text copyable code>{v}</Typography.Text> },
          { title: 'Lượt đã dùng', dataIndex: 'so_luot_da_dung', key: 'dung', align: 'right' },
          {
            title: '',
            key: 'xoa',
            width: 80,
            render: (_, m) =>
              ghi && m.so_luot_da_dung === 0 ? (
                <Popconfirm title="Xóa mã này?" okText="Xóa" cancelText="Hủy" onConfirm={() => void xoa(m.id)}>
                  <Button size="small" danger>Xóa</Button>
                </Popconfirm>
              ) : null,
          },
        ]}
      />
    </Space>
  )
}

function FormKhuyenMai({ dangSua, dong, xong }: { dangSua: KhuyenMaiChiTiet | 'moi' | null; dong: () => void; xong: () => void }) {
  const { message } = App.useApp()
  const [form] = Form.useForm<GiaTriForm>()
  const [dangLuu, setDangLuu] = useState(false)
  const [tuKhoaSp, setTuKhoaSp] = useState('')
  const phamVi = Form.useWatch('pham_vi', form)
  const loai = Form.useWatch('loai_giam', form)
  const cay = useQuery({
    queryKey: ['quan-tri', 'khuyen-mai', 'cay-danh-muc'],
    staleTime: 60_000,
    queryFn: async () => (await api.GET('/api/v1/noi-bo/danh-muc')).data ?? [],
  })
  const sp = useQuery({
    queryKey: ['quan-tri', 'khuyen-mai', 'tim-san-pham', tuKhoaSp],
    enabled: phamVi === 'san_pham',
    queryFn: async () => (await api.GET('/api/v1/noi-bo/san-pham', { params: { query: { q: tuKhoaSp || undefined, kich_thuoc: 20 } } })).data?.du_lieu ?? [],
  })
  const km = dangSua && dangSua !== 'moi' ? dangSua : null
  const tuyChonSp = new Map((sp.data ?? []).filter((s) => s.loai_san_pham !== 'thuoc_ke_don').map((s) => [s.id, `${s.ten} (${s.sku})`]))
  for (const s of km?.san_pham ?? []) if (!tuyChonSp.has(s.id)) tuyChonSp.set(s.id, s.ten)

  async function luu(v: GiaTriForm) {
    setDangLuu(true)
    const body = guiTuForm(v)
    const kq = await goi(() =>
      km
        ? api.PUT('/api/v1/noi-bo/khuyen-mai/{km_id}', { params: { path: { km_id: km.id } }, body: { ...body, phien_ban: km.phien_ban } })
        : api.POST('/api/v1/noi-bo/khuyen-mai', { body }),
    )
    setDangLuu(false)
    if (!kq.ok) {
      const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      if (Object.keys(theoTruong).length > 0) form.setFields(Object.entries(theoTruong).map(([name, e]) => ({ name: name as keyof GiaTriForm, errors: [e] })))
      return void message.error(thongDiepChung(kq.loi))
    }
    void message.success('Đã lưu khuyến mãi')
    xong()
  }
  const khoiTao: Partial<GiaTriForm> = km
    ? {
        ten: km.ten, loai_giam: km.loai_giam, gia_tri: Number(km.gia_tri), giam_toi_da: km.giam_toi_da ? Number(km.giam_toi_da) : null,
        don_toi_thieu: Number(km.don_toi_thieu), tong_luot: km.tong_luot, luot_moi_khach: km.luot_moi_khach, pham_vi: km.pham_vi,
        danh_muc_ids: km.danh_muc.map((d) => d.id), san_pham_ids: km.san_pham.map((s) => s.id), dang_hoat_dong: km.dang_hoat_dong,
        thoi_gian: [dayjs(km.bat_dau), dayjs(km.ket_thuc)] as unknown as GiaTriForm['thoi_gian'],
      }
    : { loai_giam: 'phan_tram', pham_vi: 'toan_bo', luot_moi_khach: 1, don_toi_thieu: 0, dang_hoat_dong: true }
  return (
    <Modal
      open={dangSua !== null}
      title={km ? 'Sửa khuyến mãi' : 'Tạo khuyến mãi'}
      okText="Lưu"
      cancelText="Hủy"
      confirmLoading={dangLuu}
      onCancel={dong}
      onOk={() => form.submit()}
      width={640}
      mask={{ closable: false }}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" initialValues={khoiTao} onFinish={(v) => void luu(v)} preserve={false}>
        <Form.Item name="ten" label="Tên chương trình" rules={[{ required: true, message: 'Nhập tên' }]}><Input maxLength={200} /></Form.Item>
        <Space align="start" wrap>
          <Form.Item name="loai_giam" label="Hình thức giảm"><Radio.Group optionType="button" options={[{ value: 'phan_tram', label: 'Phần trăm' }, { value: 'so_tien', label: 'Số tiền' }]} /></Form.Item>
          <Form.Item name="gia_tri" label={loai === 'so_tien' ? 'Số tiền giảm (₫)' : 'Phần trăm giảm'} rules={[{ required: true, message: 'Nhập mức giảm' }]}>
            <InputNumber min={loai === 'so_tien' ? 1 : 0.01} max={loai === 'so_tien' ? undefined : 100} precision={loai === 'so_tien' ? 0 : 2} />
          </Form.Item>
          {loai !== 'so_tien' && <Form.Item name="giam_toi_da" label="Trần giảm (₫)"><InputNumber min={1} precision={0} /></Form.Item>}
          <Form.Item name="don_toi_thieu" label="Đơn tối thiểu (₫)"><InputNumber min={0} precision={0} /></Form.Item>
        </Space>
        <Form.Item name="thoi_gian" label="Thời gian hiệu lực" rules={[{ required: true, message: 'Chọn thời gian' }]}>
          <DatePicker.RangePicker showTime format="DD/MM/YYYY HH:mm" />
        </Form.Item>
        <Space align="start" wrap>
          <Form.Item name="tong_luot" label="Tổng lượt (để trống = không giới hạn)"><InputNumber min={1} precision={0} /></Form.Item>
          <Form.Item name="luot_moi_khach" label="Lượt mỗi khách"><InputNumber min={1} precision={0} /></Form.Item>
          <Form.Item name="dang_hoat_dong" label="Đang bật" valuePropName="checked"><Switch /></Form.Item>
        </Space>
        <Form.Item name="pham_vi" label="Phạm vi áp dụng">
          <Radio.Group optionType="button" options={[{ value: 'toan_bo', label: 'Toàn bộ' }, { value: 'danh_muc', label: 'Theo danh mục' }, { value: 'san_pham', label: 'Theo sản phẩm' }]} />
        </Form.Item>
        {phamVi === 'danh_muc' && (
          <Form.Item name="danh_muc_ids" label="Danh mục (gồm cả danh mục con)" rules={[{ required: true, message: 'Chọn ít nhất một danh mục' }]}>
            <TreeSelect multiple treeDefaultExpandAll showSearch treeNodeFilterProp="title" treeData={chuyenCay(cay.data ?? [])} placeholder="Chọn danh mục" />
          </Form.Item>
        )}
        {phamVi === 'san_pham' && (
          <Form.Item name="san_pham_ids" label="Sản phẩm (không gồm thuốc kê đơn)" rules={[{ required: true, message: 'Chọn ít nhất một sản phẩm' }]}>
            <Select mode="multiple" showSearch filterOption={false} onSearch={setTuKhoaSp} placeholder="Gõ tên hoặc SKU" options={[...tuyChonSp].map(([value, label]) => ({ value, label }))} />
          </Form.Item>
        )}
        <Typography.Text type="secondary">Thuốc kê đơn không bao giờ được giảm giá, kể cả khi nằm trong phạm vi.</Typography.Text>
      </Form>
    </Modal>
  )
}

/** AD06: quản lý khuyến mãi và mã giảm giá. Chỉ Admin ghi (backend chặn thêm một lớp). */
export default function TrangKhuyenMai() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const ghi = coQuyen(usePhien((s) => s.quyen), 'promotion.manage', 'day_du')
  const [trangThai, setTrangThai] = useState<TrangThaiHieuLuc | undefined>()
  const [q, setQ] = useState('')
  const [trang, setTrang] = useState(1)
  const [dangSua, setDangSua] = useState<KhuyenMaiChiTiet | 'moi' | null>(null)
  const ds = useQuery({
    queryKey: [...KHOA_KHUYEN_MAI, 'ds', trangThai, q, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/khuyen-mai', { params: { query: { trang_thai: trangThai, q: q.trim() || undefined, trang, kich_thuoc: 20 } } })
      if (error || !data) throw error ?? new Error('Không tải được khuyến mãi')
      return data
    },
    placeholderData: (truoc) => truoc,
  })
  const lamMoi = () => queryClient.invalidateQueries({ queryKey: KHOA_KHUYEN_MAI })

  async function mo(id: number) {
    const kq = await goi(() => api.GET('/api/v1/noi-bo/khuyen-mai/{km_id}', { params: { path: { km_id: id } } }))
    if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
    setDangSua(kq.data)
  }
  async function xoa(id: number) {
    const kq = await goi(() => api.DELETE('/api/v1/noi-bo/khuyen-mai/{km_id}', { params: { path: { km_id: id } } }))
    if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
    void message.success('Đã xóa khuyến mãi')
    await lamMoi()
  }
  const cot: ColumnsType<KhuyenMaiTomTat> = [
    { title: 'Chương trình', dataIndex: 'ten', key: 'ten' },
    { title: 'Mức giảm', key: 'giam', render: (_, k) => moTaMucGiam(k, dinhDangTien) },
    { title: 'Đơn tối thiểu', key: 'min', align: 'right', render: (_, k) => dinhDangTien(k.don_toi_thieu) },
    { title: 'Hiệu lực', key: 'hl', render: (_, k) => `${dinhDangNgay(k.bat_dau, 'ngayGio')} - ${dinhDangNgay(k.ket_thuc, 'ngayGio')}` },
    { title: 'Đã dùng', key: 'dung', align: 'right', render: (_, k) => `${k.da_dung}${k.tong_luot ? ` / ${k.tong_luot}` : ''}` },
    { title: 'Trạng thái', key: 'tt', render: (_, k) => <Tag color={NHAN_TRANG_THAI[k.trang_thai].mau}>{NHAN_TRANG_THAI[k.trang_thai].nhan}</Tag> },
    {
      title: '',
      key: 'tt2',
      width: 150,
      render: (_, k) =>
        ghi ? (
          <Space>
            <Button size="small" onClick={() => void mo(k.id)}>Sửa</Button>
            <Popconfirm title="Xóa khuyến mãi này?" okText="Xóa" cancelText="Hủy" onConfirm={() => void xoa(k.id)}>
              <Button size="small" danger>Xóa</Button>
            </Popconfirm>
          </Space>
        ) : null,
    },
  ]
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Input.Search allowClear placeholder="Tên chương trình" style={{ width: 260 }} onSearch={(v) => { setQ(v); setTrang(1) }} />
        <Select<TrangThaiHieuLuc> allowClear placeholder="Trạng thái" style={{ width: 160 }} value={trangThai} onChange={(v) => { setTrangThai(v); setTrang(1) }} options={(Object.keys(NHAN_TRANG_THAI) as TrangThaiHieuLuc[]).map((v) => ({ value: v, label: NHAN_TRANG_THAI[v].nhan }))} />
        {ghi && <Button type="primary" onClick={() => setDangSua('moi')}>Tạo khuyến mãi</Button>}
      </Space>
      {ds.isError && <Alert type="error" showIcon message="Không tải được danh sách khuyến mãi" />}
      <Table<KhuyenMaiTomTat>
        rowKey="id"
        columns={cot}
        dataSource={ds.data?.du_lieu ?? []}
        loading={ds.isLoading}
        expandable={{ expandedRowRender: (k) => <MaGiamGia id={k.id} ghi={ghi} />, expandIcon: undefined }}
        pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }}
        scroll={{ x: 'max-content' }}
      />
      <FormKhuyenMai dangSua={dangSua} dong={() => setDangSua(null)} xong={() => { setDangSua(null); void lamMoi() }} />
    </Space>
  )
}
