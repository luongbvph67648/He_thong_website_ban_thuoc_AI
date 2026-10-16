import { PrinterOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Card, Checkbox, Col, Form, Input, InputNumber, Modal, Radio, Row, Select, Space, Table, Tag, Typography, Upload } from 'antd'
import type { UploadFile } from 'antd'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { chuanHoaSdt } from '../../../lib/dienThoai'
import { dinhDangTien } from '../../../lib/dinhDang'
import HoaDonIn from './HoaDonIn'
import { dongTuSanPham, themDongPos, tongPos, type DongPos, type SanPhamPos } from './pos'

type CanhBao = components['schemas']['CanhBaoPosRa']
type HoaDon = components['schemas']['HoaDonRa']
type YeuCauQuay = components['schemas']['YeuCauQuayRa']

const MUC = { chong_chi_dinh: ['red', 'Chống chỉ định'], nghiem_trong: ['volcano', 'Nghiêm trọng'], trung_binh: ['orange', 'Trung bình'], nhe: ['blue', 'Nhẹ'] } as const

/** DS08: bán tại quầy. Quét mã vạch hoặc tìm thuốc, thu tiền mặt/chuyển khoản, xuất kho FEFO ngay, in hóa đơn. */
export default function TrangPos() {
  const { message } = App.useApp()
  const oTim = useRef<HTMLInputElement>(null)
  const khoaBan = useRef(crypto.randomUUID())
  const [tuKhoa, setTuKhoa] = useState('')
  const [tim, setTim] = useState('')
  const [dong, setDong] = useState<DongPos[]>([])
  const [sdtKhach, setSdtKhach] = useState('')
  const [canhBao, setCanhBao] = useState<CanhBao | null>(null)
  const [yeuCau, setYeuCau] = useState<YeuCauQuay | null>(null)
  const [pt, setPt] = useState<'tien_mat' | 'chuyen_khoan'>('tien_mat')
  const [khachDua, setKhachDua] = useState<number | null>(null)
  const [xacNhanCb, setXacNhanCb] = useState(false)
  const [xacNhanTrung, setXacNhanTrung] = useState(false)
  const [dangBan, setDangBan] = useState(false)
  const [hoaDon, setHoaDon] = useState<HoaDon | null>(null)
  const [formDon] = Form.useForm<{ ho_ten: string; tuoi: string; anh: UploadFile[] }>()
  const [dangLap, setDangLap] = useState(false)

  const tong = tongPos(dong)
  const coKeDon = dong.some((d) => d.ke_don)
  const sdt = chuanHoaSdt(sdtKhach)

  const ketQua = useQuery({
    queryKey: ['pos', 'san-pham', tim],
    enabled: tim.trim().length >= 1,
    queryFn: async () => (await api.GET('/api/v1/noi-bo/pos/san-pham', { params: { query: { q: tim.trim() } } })).data ?? [],
  })

  const them = useCallback((sp: SanPhamPos, donViId?: number, soLuong = 1) => {
    const d = dongTuSanPham(sp, donViId, soLuong)
    if (!d) return
    setDong((ds) => themDongPos(ds, d))
    setTuKhoa('')
    setTim('')
    oTim.current?.focus()
  }, [])

  async function timHoacQuet() {
    const q = tuKhoa.trim()
    if (!q) return
    setTim(q)
    // Máy quét gõ nguyên mã rồi Enter: nếu khớp đúng một sản phẩm theo mã vạch thì thêm luôn.
    const r = await goi(() => api.GET('/api/v1/noi-bo/pos/san-pham', { params: { query: { q } } }))
    if (r.ok && r.data.length === 1 && r.data[0].don_vi_khop_ma_vach != null) them(r.data[0])
  }

  useEffect(() => {
    if (dong.length === 0) return
    let huy = false
    void goi(() =>
      api.POST('/api/v1/noi-bo/pos/canh-bao', {
        body: { dong: dong.map((d) => ({ san_pham_id: d.san_pham_id, don_vi_id: d.don_vi_id, so_luong: d.so_luong })), sdt_khach: sdt },
      }),
    ).then((r) => {
      if (!huy && r.ok) setCanhBao(r.data)
    })
    return () => {
      huy = true
    }
  }, [dong, sdt])

  const canhBaoHienTai = dong.length > 0 ? canhBao : null
  const canXacNhan = canhBaoHienTai?.can_xac_nhan ?? false
  const thua = pt === 'tien_mat' && khachDua != null ? khachDua - tong : null
  const thieuTien = pt === 'tien_mat' && (khachDua == null || khachDua < tong)
  const thieuDon = coKeDon && !yeuCau
  const khongBan = dong.length === 0 || thieuTien || thieuDon || (canXacNhan && !xacNhanCb) || ((yeuCau?.trung_anh.length ?? 0) > 0 && !xacNhanTrung)

  async function lapYeuCau(v: { ho_ten: string; tuoi: string; anh: UploadFile[] }) {
    const files = v.anh.map((f) => f.originFileObj).filter((f): f is NonNullable<typeof f> => !!f)
    setDangLap(true)
    const r = await goi(() =>
      api.POST('/api/v1/noi-bo/pos/don-thuoc', {
        body: { anh: [], ho_ten: v.ho_ten },
        bodySerializer: () => {
          const fd = new FormData()
          files.forEach((f) => fd.append('anh', f))
          fd.append('ho_ten', v.ho_ten)
          if (v.tuoi) fd.append('tuoi_hoac_nam_sinh', v.tuoi)
          return fd
        },
      }),
    )
    setDangLap(false)
    if (r.ok) setYeuCau(r.data)
    else void message.error(thongDiepChung(r.loi))
  }

  async function ban() {
    setDangBan(true)
    const r = await goi(() =>
      api.POST('/api/v1/noi-bo/pos/don', {
        headers: { 'Idempotency-Key': khoaBan.current },
        body: {
          dong: dong.map((d) => ({ san_pham_id: d.san_pham_id, don_vi_id: d.don_vi_id, so_luong: d.so_luong })),
          sdt_khach: sdt,
          yeu_cau_don_thuoc_id: coKeDon ? (yeuCau?.id ?? null) : null,
          phuong_thuc_thu: pt,
          tien_khach_dua: pt === 'tien_mat' && khachDua != null ? String(khachDua) : null,
          xac_nhan_canh_bao: xacNhanCb,
          xac_nhan_trung_anh: xacNhanTrung,
        },
      }),
    )
    setDangBan(false)
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    setHoaDon(r.data.hoa_don)
  }

  function banMoi() {
    setHoaDon(null)
    setDong([])
    setSdtKhach('')
    setYeuCau(null)
    setCanhBao(null)
    setKhachDua(null)
    setXacNhanCb(false)
    setXacNhanTrung(false)
    formDon.resetFields()
    khoaBan.current = crypto.randomUUID()
    oTim.current?.focus()
  }

  useEffect(() => {
    const f9 = (e: KeyboardEvent) => {
      if (e.key === 'F9') e.preventDefault()
    }
    window.addEventListener('keydown', f9)
    return () => window.removeEventListener('keydown', f9)
  }, [])

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Bán tại quầy</Typography.Title>
      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card size="small" title="Quét mã vạch hoặc tìm thuốc">
            <Input
              ref={(el) => {
                oTim.current = el?.input ?? null
              }}
              autoFocus
              allowClear
              size="large"
              placeholder="Quét mã vạch, hoặc gõ tên thuốc / hoạt chất rồi Enter"
              value={tuKhoa}
              onChange={(e) => setTuKhoa(e.target.value)}
              onPressEnter={() => void timHoacQuet()}
            />
            <Space orientation="vertical" style={{ width: '100%', marginTop: 8 }}>
              {(ketQua.data ?? []).map((sp) => (
                <KetQuaTim key={sp.id} sp={sp} them={them} />
              ))}
              {tim && !ketQua.isLoading && (ketQua.data ?? []).length === 0 && <Typography.Text type="secondary">Không tìm thấy sản phẩm</Typography.Text>}
            </Space>
          </Card>
          <Table<DongPos>
            style={{ marginTop: 16 }}
            size="small"
            pagination={false}
            rowKey={(r) => `${r.san_pham_id}-${r.don_vi_id}`}
            dataSource={dong}
            locale={{ emptyText: 'Chưa có sản phẩm nào' }}
            columns={[
              { title: 'Sản phẩm', render: (_, r) => <>{r.ten} {r.ke_don && <Tag color="red">Kê đơn</Tag>}</> },
              { title: 'Đơn vị', dataIndex: 'ten_don_vi' },
              { title: 'Đơn giá', align: 'right', render: (_, r) => dinhDangTien(r.gia) },
              {
                title: 'SL',
                render: (_, r) => (
                  <InputNumber min={1} max={9999} value={r.so_luong} onChange={(v) => setDong((ds) => ds.map((x) => (x === r ? { ...x, so_luong: v ?? 1 } : x)))} />
                ),
              },
              { title: 'Thành tiền', align: 'right', render: (_, r) => dinhDangTien(Math.round(Number(r.gia)) * r.so_luong) },
              { title: '', render: (_, r) => <Button size="small" danger onClick={() => setDong((ds) => ds.filter((x) => x !== r))}>Bỏ</Button> },
            ]}
          />
        </Col>
        <Col xs={24} lg={10}>
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <Card size="small" title="Khách hàng (không bắt buộc)">
              <Input placeholder="SĐT khách đã đăng ký" inputMode="tel" value={sdtKhach} onChange={(e) => setSdtKhach(e.target.value)} status={sdtKhach && !sdt ? 'error' : undefined} />
            </Card>
            {coKeDon && (
              <Card size="small" title="Đơn thuốc (bắt buộc cho thuốc kê đơn)">
                {yeuCau ? (
                  <Space orientation="vertical">
                    <Tag color="green">Đã lập yêu cầu {yeuCau.ma_yeu_cau} · {yeuCau.ho_ten}</Tag>
                    {yeuCau.trung_anh.length > 0 && (
                      <Alert type="error" showIcon title={`Ảnh trùng đơn đã dùng: ${yeuCau.trung_anh.join(', ')}`} />
                    )}
                  </Space>
                ) : (
                  <Form form={formDon} layout="vertical" onFinish={(v) => void lapYeuCau(v)} initialValues={{ anh: [] }}>
                    <Form.Item name="ho_ten" label="Họ tên người bệnh" rules={[{ required: true, message: 'Nhập họ tên' }]}><Input maxLength={150} /></Form.Item>
                    <Form.Item name="tuoi" label="Tuổi hoặc năm sinh"><Input maxLength={20} /></Form.Item>
                    <Form.Item
                      name="anh"
                      label="Ảnh đơn thuốc"
                      valuePropName="fileList"
                      getValueFromEvent={(e: { fileList: UploadFile[] }) => e.fileList}
                      rules={[{ validator: (_, v: UploadFile[]) => (v?.length ? Promise.resolve() : Promise.reject(new Error('Chọn ít nhất một ảnh'))) }]}
                    >
                      <Upload multiple listType="picture" accept="image/jpeg,image/png,image/webp" maxCount={5} beforeUpload={() => false}>
                        <Button>Chọn ảnh đơn</Button>
                      </Upload>
                    </Form.Item>
                    <Button htmlType="submit" loading={dangLap}>Lập yêu cầu đơn thuốc</Button>
                  </Form>
                )}
              </Card>
            )}
            {canhBaoHienTai && (canhBaoHienTai.tuong_tac.length > 0 || canhBaoHienTai.di_ung.length > 0) && (
              <Card size="small" title="Cảnh báo">
                <Space orientation="vertical" style={{ width: '100%' }}>
                  {canhBaoHienTai.di_ung.map((c) => <Alert key={`${c.san_pham_id}-${c.hoat_chat_id}`} type="error" showIcon title={`${c.ten_san_pham} chứa ${c.ten_hoat_chat}: khách khai dị ứng`} />)}
                  {canhBaoHienTai.tuong_tac.map((c) => (
                    <Alert
                      key={`${c.san_pham_a_id}-${c.san_pham_b_id}-${c.hoat_chat_a_id}-${c.hoat_chat_b_id}`}
                      type={c.muc_do === 'chong_chi_dinh' || c.muc_do === 'nghiem_trong' ? 'error' : 'warning'}
                      showIcon
                      title={<><Tag color={MUC[c.muc_do][0]}>{MUC[c.muc_do][1]}</Tag>{c.ten_hoat_chat_a} + {c.ten_hoat_chat_b}</>}
                      description={c.khuyen_cao}
                    />
                  ))}
                  {canXacNhan && <Checkbox checked={xacNhanCb} onChange={(e) => setXacNhanCb(e.target.checked)}>Tôi đã tư vấn cho khách về các cảnh báo trên</Checkbox>}
                </Space>
              </Card>
            )}
            {(yeuCau?.trung_anh.length ?? 0) > 0 && (
              <Checkbox checked={xacNhanTrung} onChange={(e) => setXacNhanTrung(e.target.checked)}>Tôi đã kiểm tra ảnh trùng và vẫn bán</Checkbox>
            )}
            <Card size="small" title="Thanh toán">
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Typography.Title level={3} style={{ margin: 0 }}>Tổng: {dinhDangTien(tong)}</Typography.Title>
                <Radio.Group
                  value={pt}
                  onChange={(e) => setPt(e.target.value)}
                  options={[{ value: 'tien_mat', label: 'Tiền mặt' }, { value: 'chuyen_khoan', label: 'Chuyển khoản' }]}
                />
                {pt === 'tien_mat' && (
                  <>
                    <InputNumber aria-label="Tiền khách đưa" style={{ width: '100%' }} min={0} step={1000} placeholder="Tiền khách đưa" value={khachDua} onChange={setKhachDua} />
                    {thua != null && <Typography.Text type={thua < 0 ? 'danger' : undefined}>{thua < 0 ? `Còn thiếu ${dinhDangTien(-thua)}` : `Tiền thối: ${dinhDangTien(thua)}`}</Typography.Text>}
                  </>
                )}
                <Button type="primary" size="large" block disabled={khongBan} loading={dangBan} onClick={() => void ban()}>Thanh toán và in hóa đơn</Button>
              </Space>
            </Card>
          </Space>
        </Col>
      </Row>
      <Modal
        title="Đã bán hàng"
        open={!!hoaDon}
        onCancel={banMoi}
        footer={[
          <Button key="in" icon={<PrinterOutlined />} onClick={() => window.print()}>In hóa đơn</Button>,
          <Button key="moi" type="primary" onClick={banMoi}>Đơn mới</Button>,
        ]}
        destroyOnHidden
      >
        {hoaDon && <HoaDonIn hd={hoaDon} />}
      </Modal>
    </Space>
  )
}

function KetQuaTim({ sp, them }: { sp: SanPhamPos; them: (sp: SanPhamPos, donViId?: number, soLuong?: number) => void }) {
  const [donVi, setDonVi] = useState(sp.don_vi_khop_ma_vach ?? sp.don_vi[0]?.id)
  const [sl, setSl] = useState(1)
  return (
    <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
      <span>
        {sp.ten} {sp.loai_san_pham === 'thuoc_ke_don' && <Tag color="red">Kê đơn</Tag>} {sp.co_lo_can_han && <Tag color="orange">Có lô cận hạn</Tag>}
        <Typography.Text type="secondary"> · tồn {sp.ton_quay} {sp.don_vi_co_so}</Typography.Text>
      </span>
      <Space>
        <Select value={donVi} onChange={setDonVi} style={{ width: 130 }} options={sp.don_vi.map((x) => ({ value: x.id, label: `${x.ten_don_vi} · ${dinhDangTien(x.gia_ban)}` }))} />
        <InputNumber min={1} max={9999} value={sl} onChange={(v) => setSl(v ?? 1)} />
        <Button size="small" type="primary" onClick={() => donVi && them(sp, donVi, sl)}>Thêm</Button>
      </Space>
    </Space>
  )
}
