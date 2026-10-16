import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Card, Form, Input, InputNumber, Radio, Result, Select, Space, Table, Tag, Typography } from 'antd'
import { useRef, useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import type { components } from '../../../api/schema'
import { dinhDangTien } from '../../../lib/dinhDang'
import { tamTinh, themDong, type DongHo, type DonHoVao, type KhachTim } from './donHo'

type SanPhamThe = components['schemas']['SanPhamThe']
type ChiTiet = components['schemas']['SanPhamChiTietCongKhai']
type DonHoRa = components['schemas']['DonHoRa']

interface FormHo {
  ten_nguoi_nhan: string
  sdt_nguoi_nhan: string
  hinh_thuc_nhan: DonHoVao['hinh_thuc_nhan']
  phuong_thuc_tt: DonHoVao['phuong_thuc_tt']
  dia_chi_chi_tiet?: string
  ma_tinh?: string
  ma_phuong_xa?: string
  ma_giam_gia?: string
  ghi_chu?: string
}

/** DS07: dược sĩ lập đơn hộ khách gọi điện. Thuốc kê đơn bị chặn (cả ở máy chủ); đơn online cần khách có tài khoản. */
export default function TrangTaoDonHo() {
  const { message } = App.useApp()
  const [form] = Form.useForm<FormHo>()
  const khoaLap = useRef(crypto.randomUUID())
  const [sdtTim, setSdtTim] = useState('')
  const [khach, setKhach] = useState<KhachTim | null>(null)
  const [daTim, setDaTim] = useState(false)
  const [dong, setDong] = useState<DongHo[]>([])
  const [tuKhoa, setTuKhoa] = useState('')
  const [chon, setChon] = useState<ChiTiet | null>(null)
  const [donViId, setDonViId] = useState<number | null>(null)
  const [soLuong, setSoLuong] = useState(1)
  const [dangGui, setDangGui] = useState(false)
  const [ketQua, setKetQua] = useState<DonHoRa | null>(null)
  const hinhThuc = Form.useWatch('hinh_thuc_nhan', form)
  const maTinh = Form.useWatch('ma_tinh', form)

  const goiY = useQuery({
    queryKey: ['don-ho', 'tim', tuKhoa],
    enabled: tuKhoa.trim().length >= 2,
    queryFn: async () => (await api.GET('/api/v1/tim-kiem', { params: { query: { q: tuKhoa.trim(), kich_thuoc: 10 } } })).data?.du_lieu ?? [],
  })
  const tinh = useQuery({
    queryKey: ['dia-gioi', 'tinh'],
    staleTime: Infinity,
    queryFn: async () => (await api.GET('/api/v1/dia-gioi/tinh')).data ?? [],
  })
  const xa = useQuery({
    queryKey: ['dia-gioi', 'xa', maTinh],
    enabled: !!maTinh,
    staleTime: Infinity,
    queryFn: async () => (await api.GET('/api/v1/dia-gioi/tinh/{ma_tinh}/xa', { params: { path: { ma_tinh: maTinh! } } })).data ?? [],
  })

  async function timKhach() {
    const r = await goi(() => api.GET('/api/v1/noi-bo/don-ho/khach', { params: { query: { sdt: sdtTim.trim() } } }))
    setDaTim(true)
    if (r.ok) {
      setKhach(r.data)
      form.setFieldsValue({ ten_nguoi_nhan: r.data.ho_ten, sdt_nguoi_nhan: r.data.so_dien_thoai })
    } else {
      setKhach(null)
      if (r.loi && r.loi.ma_loi !== 'KHONG_TIM_THAY') void message.error(thongDiepChung(r.loi))
    }
  }

  async function chonSanPham(id: number) {
    const sp = goiY.data?.find((s: SanPhamThe) => s.id === id)
    if (!sp) return
    if (sp.loai_san_pham === 'thuoc_ke_don') {
      void message.warning('Thuốc kê đơn không bán qua điện thoại: dùng Yêu cầu đơn thuốc để dược sĩ tư vấn.')
      return
    }
    const r = await goi(() => api.GET('/api/v1/san-pham/{slug}', { params: { path: { slug: sp.slug } } }))
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    setChon(r.data)
    setDonViId(r.data.don_vi.find((d) => d.la_mac_dinh)?.id ?? r.data.don_vi[0]?.id ?? null)
    setSoLuong(1)
  }

  function themVaoDon() {
    const dv = chon?.don_vi.find((d) => d.id === donViId)
    if (!chon || !dv) return
    setDong((ds) => themDong(ds, { san_pham_id: chon.id, don_vi_id: dv.id, ten: chon.ten, ten_don_vi: dv.ten_don_vi, gia: dv.gia_ban, so_luong: soLuong }))
    setChon(null)
    setTuKhoa('')
  }

  async function gui(v: FormHo) {
    if (dong.length === 0) return void message.error('Chưa có sản phẩm nào trong đơn')
    const giao = v.hinh_thuc_nhan === 'giao_tan_noi'
    const body: DonHoVao = {
      sdt_khach: khach?.so_dien_thoai ?? null,
      ten_nguoi_nhan: v.ten_nguoi_nhan,
      sdt_nguoi_nhan: v.sdt_nguoi_nhan,
      hinh_thuc_nhan: v.hinh_thuc_nhan,
      phuong_thuc_tt: v.phuong_thuc_tt,
      dia_chi: giao ? { dia_chi_chi_tiet: v.dia_chi_chi_tiet ?? '', ma_tinh: v.ma_tinh ?? '', ma_phuong_xa: v.ma_phuong_xa ?? '' } : null,
      dong: dong.map((d) => ({ san_pham_id: d.san_pham_id, don_vi_id: d.don_vi_id, so_luong: d.so_luong })),
      ma_giam_gia: v.ma_giam_gia?.trim() || null,
      ghi_chu: v.ghi_chu?.trim() || null,
    }
    setDangGui(true)
    const r = await goi(() => api.POST('/api/v1/noi-bo/don-ho', { body, headers: { 'Idempotency-Key': khoaLap.current } }))
    setDangGui(false)
    if (r.ok) {
      setKetQua(r.data)
      khoaLap.current = crypto.randomUUID()
      return
    }
    const theoTruong = r.loi ? loiTheoTruong(r.loi) : {}
    if (Object.keys(theoTruong).length > 0) {
      form.setFields(Object.entries(theoTruong).map(([name, e]) => ({ name: name as keyof FormHo, errors: [e] })))
    }
    void message.error(thongDiepChung(r.loi))
  }

  function lapDonMoi() {
    setKetQua(null)
    setKhach(null)
    setDaTim(false)
    setSdtTim('')
    setDong([])
    form.resetFields()
  }

  if (ketQua) {
    const lien = ketQua.lien_ket_thanh_toan ? `${window.location.origin}${ketQua.lien_ket_thanh_toan}` : null
    return (
      <Result
        status="success"
        title={`Đã lập đơn ${ketQua.don.ma_don}`}
        subTitle={lien ? 'Đơn chờ khách thanh toán online. Gửi link cho khách:' : 'Đơn đã được xác nhận, chuyển cho kho soạn hàng.'}
        extra={[
          lien && <Input key="lien" readOnly value={lien} style={{ maxWidth: 480 }} onFocus={(e) => e.target.select()} />,
          <Button key="moi" type="primary" onClick={lapDonMoi}>Lập đơn khác</Button>,
        ]}
      >
        <Typography.Paragraph>Tổng tiền: <b>{dinhDangTien(ketQua.don.tong_tien)}</b></Typography.Paragraph>
      </Result>
    )
  }

  const tamTinhDon = tamTinh(dong)
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%', maxWidth: 960 }}>
      <Typography.Title level={3} style={{ margin: 0 }}>Tạo đơn hộ khách</Typography.Title>
      <Card size="small" title="Khách hàng">
        <Space.Compact style={{ maxWidth: 420 }}>
          <Input placeholder="SĐT khách (nếu đã có tài khoản)" value={sdtTim} onChange={(e) => setSdtTim(e.target.value)} onPressEnter={() => void timKhach()} />
          <Button onClick={() => void timKhach()} disabled={sdtTim.trim() === ''}>Tìm khách</Button>
        </Space.Compact>
        {khach && <Alert style={{ marginTop: 8 }} type="success" showIcon message={`Khách có tài khoản: ${khach.ho_ten} · ${khach.so_dien_thoai}`} />}
        {daTim && !khach && <Alert style={{ marginTop: 8 }} type="warning" showIcon message="Chưa có tài khoản với số này: chỉ lập được đơn COD, nhập thông tin người nhận bên dưới." />}
      </Card>
      <Card size="small" title="Sản phẩm">
        <Space wrap>
          <Select
            showSearch
            style={{ width: 360 }}
            placeholder="Tìm sản phẩm theo tên"
            filterOption={false}
            value={null}
            searchValue={tuKhoa}
            onSearch={setTuKhoa}
            onSelect={(id) => { if (id != null) void chonSanPham(id) }}
            notFoundContent={tuKhoa.trim().length < 2 ? 'Nhập ít nhất 2 ký tự' : 'Không tìm thấy'}
            options={(goiY.data ?? []).map((s: SanPhamThe) => ({
              value: s.id,
              label: (
                <span>
                  {s.ten} {s.loai_san_pham === 'thuoc_ke_don' && <Tag color="red">Kê đơn</Tag>}
                </span>
              ),
            }))}
          />
          {chon && (
            <>
              <b>{chon.ten}</b>
              <Select
                style={{ width: 160 }}
                value={donViId}
                onChange={setDonViId}
                options={chon.don_vi.map((d) => ({ value: d.id, label: `${d.ten_don_vi} · ${dinhDangTien(d.gia_ban)}` }))}
              />
              <InputNumber min={1} max={9999} value={soLuong} onChange={(v) => setSoLuong(v ?? 1)} />
              <Button type="primary" onClick={themVaoDon}>Thêm vào đơn</Button>
            </>
          )}
        </Space>
        <Table<DongHo>
          style={{ marginTop: 12 }}
          size="small"
          pagination={false}
          rowKey={(d) => `${d.san_pham_id}-${d.don_vi_id}`}
          dataSource={dong}
          locale={{ emptyText: 'Chưa có sản phẩm' }}
          columns={[
            { title: 'Sản phẩm', key: 'ten', render: (_, d) => `${d.ten} (${d.ten_don_vi})` },
            { title: 'SL', dataIndex: 'so_luong', key: 'sl', align: 'right' },
            { title: 'Đơn giá', key: 'gia', align: 'right', render: (_, d) => dinhDangTien(d.gia) },
            { title: 'Thành tiền', key: 'tt', align: 'right', render: (_, d) => dinhDangTien(Math.round(Number(d.gia)) * d.so_luong) },
            { title: '', key: 'xoa', render: (_, d) => <Button type="link" danger onClick={() => setDong((ds) => ds.filter((x) => x !== d))}>Xóa</Button> },
          ]}
          summary={() => (dong.length > 0 ? <Table.Summary.Row><Table.Summary.Cell index={0} colSpan={3}>Tạm tính (chưa gồm giảm giá, phí ship)</Table.Summary.Cell><Table.Summary.Cell index={1} align="right"><b>{dinhDangTien(tamTinhDon)}</b></Table.Summary.Cell><Table.Summary.Cell index={2} /></Table.Summary.Row> : null)}
        />
      </Card>
      <Card size="small" title="Người nhận và thanh toán">
        <Form<FormHo> form={form} layout="vertical" initialValues={{ hinh_thuc_nhan: 'giao_tan_noi', phuong_thuc_tt: 'cod' }} onFinish={(v) => void gui(v)}>
          <Space wrap align="start">
            <Form.Item label="Tên người nhận" name="ten_nguoi_nhan" rules={[{ required: true, message: 'Nhập tên người nhận' }]}><Input style={{ width: 240 }} maxLength={150} /></Form.Item>
            <Form.Item label="SĐT người nhận" name="sdt_nguoi_nhan" rules={[{ required: true, message: 'Nhập số điện thoại' }]}><Input style={{ width: 200 }} maxLength={20} /></Form.Item>
          </Space>
          <Form.Item label="Hình thức nhận" name="hinh_thuc_nhan">
            <Radio.Group options={[{ value: 'giao_tan_noi', label: 'Giao tận nơi' }, { value: 'nhan_tai_nha_thuoc', label: 'Nhận tại nhà thuốc' }]} />
          </Form.Item>
          {hinhThuc === 'giao_tan_noi' && (
            <Space wrap align="start">
              <Form.Item label="Địa chỉ chi tiết" name="dia_chi_chi_tiet" rules={[{ required: true, message: 'Nhập địa chỉ' }]}><Input style={{ width: 280 }} maxLength={300} /></Form.Item>
              <Form.Item label="Tỉnh/thành" name="ma_tinh" rules={[{ required: true, message: 'Chọn tỉnh/thành' }]}>
                <Select showSearch optionFilterProp="label" style={{ width: 200 }} onChange={() => form.setFieldValue('ma_phuong_xa', undefined)} options={(tinh.data ?? []).map((t) => ({ value: t.ma, label: t.ten }))} />
              </Form.Item>
              <Form.Item label="Phường/xã" name="ma_phuong_xa" rules={[{ required: true, message: 'Chọn phường/xã' }]}>
                <Select showSearch optionFilterProp="label" style={{ width: 200 }} options={(xa.data ?? []).map((x) => ({ value: x.ma, label: x.ten }))} />
              </Form.Item>
            </Space>
          )}
          <Form.Item label="Thanh toán" name="phuong_thuc_tt" extra={khach ? undefined : 'Thanh toán online cần khách có tài khoản (để nhận link thanh toán).'}>
            <Radio.Group
              options={[
                { value: 'cod', label: 'COD (trả khi nhận)' },
                { value: 'vnpay', label: 'VNPay', disabled: !khach },
                { value: 'momo', label: 'MoMo', disabled: !khach },
              ]}
            />
          </Form.Item>
          <Space wrap align="start">
            <Form.Item label="Mã giảm giá" name="ma_giam_gia" extra={khach ? undefined : 'Chỉ áp dụng cho khách có tài khoản'}><Input style={{ width: 200 }} maxLength={40} disabled={!khach} /></Form.Item>
            <Form.Item label="Ghi chú" name="ghi_chu"><Input.TextArea style={{ width: 360 }} rows={2} maxLength={500} /></Form.Item>
          </Space>
          <Button type="primary" htmlType="submit" loading={dangGui} disabled={dong.length === 0}>Lập đơn</Button>
        </Form>
      </Card>
    </Space>
  )
}
