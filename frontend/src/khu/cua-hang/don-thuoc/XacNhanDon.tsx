import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Form, Input, Radio, Select, Space, Table, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { thongDiepChung, type KetQuaGoi } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { chuanHoaSdt } from '../../../lib/dienThoai'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { NHAN_PHUONG_THUC } from '../gio-hang/thanhToan'
import { chuyenSangCong } from '../gio-hang/thanhToanOnline'

type DonXacNhan = components['schemas']['DonXacNhanRa']
type XacNhanVao = components['schemas']['XacNhanVao']

interface Props {
  duLieu: DonXacNhan
  /** Thành viên được chọn địa chỉ từ sổ; khách vãng lai nhập tay. */
  thanhVien: boolean
  xacNhan: (body: XacNhanVao) => Promise<KetQuaGoi<DonXacNhan>>
  tuChoi: () => Promise<KetQuaGoi<unknown>>
  thanhToan: () => Promise<KetQuaGoi<{ url_thanh_toan: string }>>
  /** Gọi sau khi trạng thái đơn đổi, để trang cha tải lại. */
  lamMoi: () => void
}

interface FormXn {
  hinh_thuc_nhan: 'giao_tan_noi' | 'nhan_tai_nha_thuoc'
  phuong_thuc_tt: 'cod' | 'vnpay' | 'momo'
  dia_chi_id?: number
  ten_nguoi_nhan?: string
  sdt_nguoi_nhan?: string
  dia_chi_chi_tiet?: string
  ma_tinh?: string
  ma_phuong_xa?: string
  ghi_chu?: string
}

/** KTV07: xác nhận đơn do dược sĩ tạo từ đơn thuốc (chọn cách nhận, địa chỉ, thanh toán) hoặc từ chối; thanh toán online. */
export default function XacNhanDon({ duLieu, thanhVien, xacNhan, tuChoi, thanhToan, lamMoi }: Props) {
  const { message, modal } = App.useApp()
  const [form] = Form.useForm<FormXn>()
  const [dang, setDang] = useState(false)
  const don = duLieu.don
  const hinhThuc = Form.useWatch('hinh_thuc_nhan', form)
  const diaChiId = Form.useWatch('dia_chi_id', form)
  const maTinh = Form.useWatch('ma_tinh', form)

  const soDiaChi = useQuery({
    queryKey: ['toi', 'dia-chi'],
    enabled: thanhVien && duLieu.co_the_xac_nhan,
    queryFn: async () => (await api.GET('/api/v1/toi/dia-chi')).data ?? [],
  })
  const tinh = useQuery({
    queryKey: ['dia-gioi', 'tinh'],
    staleTime: Infinity,
    enabled: duLieu.co_the_xac_nhan,
    queryFn: async () => (await api.GET('/api/v1/dia-gioi/tinh')).data ?? [],
  })
  const xa = useQuery({
    queryKey: ['dia-gioi', 'xa', maTinh],
    enabled: !!maTinh,
    staleTime: Infinity,
    queryFn: async () => (await api.GET('/api/v1/dia-gioi/tinh/{ma_tinh}/xa', { params: { path: { ma_tinh: maTinh! } } })).data ?? [],
  })

  async function gui(v: FormXn) {
    const giao = v.hinh_thuc_nhan === 'giao_tan_noi'
    const body: XacNhanVao = {
      hinh_thuc_nhan: v.hinh_thuc_nhan,
      phuong_thuc_tt: v.phuong_thuc_tt,
      ghi_chu: v.ghi_chu?.trim() || null,
    }
    if (giao && v.dia_chi_id) body.dia_chi_id = v.dia_chi_id
    else if (giao) {
      body.dia_chi = { dia_chi_chi_tiet: v.dia_chi_chi_tiet ?? '', ma_tinh: v.ma_tinh ?? '', ma_phuong_xa: v.ma_phuong_xa ?? '' }
      body.ten_nguoi_nhan = v.ten_nguoi_nhan
      body.sdt_nguoi_nhan = chuanHoaSdt(v.sdt_nguoi_nhan ?? '') ?? v.sdt_nguoi_nhan
    }
    setDang(true)
    const r = await xacNhan(body)
    setDang(false)
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    void message.success(v.phuong_thuc_tt === 'cod' ? 'Đã xác nhận đơn hàng' : 'Đã xác nhận, hãy thanh toán để hoàn tất')
    lamMoi()
  }

  function xacNhanTuChoi() {
    modal.confirm({
      title: 'Từ chối đơn hàng này?',
      content: 'Hàng đang giữ cho bạn sẽ được nhả. Dược sĩ có thể tạo lại đơn nếu cần.',
      okText: 'Từ chối đơn',
      okButtonProps: { danger: true },
      cancelText: 'Giữ lại',
      onOk: async () => {
        const r = await tuChoi()
        if (!r.ok) return void message.error(thongDiepChung(r.loi))
        lamMoi()
      },
    })
  }

  async function traTien() {
    setDang(true)
    const r = await thanhToan()
    setDang(false)
    if (r.ok) chuyenSangCong.di(r.data.url_thanh_toan)
    else void message.error(thongDiepChung(r.loi))
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Descriptions
        bordered
        size="small"
        column={1}
        items={[
          { key: 'ma', label: 'Mã đơn', children: don.ma_don },
          { key: 'tt', label: 'Trạng thái', children: don.trang_thai },
          ...(don.han_xac_nhan && duLieu.co_the_xac_nhan ? [{ key: 'han', label: 'Xác nhận trước', children: dinhDangNgay(don.han_xac_nhan, 'ngayGio') }] : []),
          ...(don.ghi_chu ? [{ key: 'gc', label: 'Lời dặn của dược sĩ', children: don.ghi_chu }] : []),
          { key: 'tam', label: 'Tạm tính', children: dinhDangTien(don.tam_tinh) },
          { key: 'ship', label: 'Phí vận chuyển', children: duLieu.co_the_xac_nhan ? 'Tính sau khi chọn địa chỉ' : dinhDangTien(don.phi_van_chuyen) },
          { key: 'tong', label: 'Tổng cộng', children: <b>{dinhDangTien(don.tong_tien)}</b> },
        ]}
      />
      <Table
        size="small"
        rowKey={(d) => `${d.san_pham_id}-${d.ten_don_vi}`}
        pagination={false}
        dataSource={don.dong}
        columns={[
          { title: 'Sản phẩm', dataIndex: 'ten_san_pham' },
          { title: 'Đơn vị', dataIndex: 'ten_don_vi' },
          { title: 'SL', dataIndex: 'so_luong', align: 'right' },
          { title: 'Thành tiền', dataIndex: 'thanh_tien', align: 'right', render: (v: string) => dinhDangTien(v) },
        ]}
      />
      {duLieu.co_the_thanh_toan && (
        <Alert
          type="info"
          showIcon
          title={`Đơn đang chờ thanh toán ${don.phuong_thuc_tt ? NHAN_PHUONG_THUC[don.phuong_thuc_tt as 'cod' | 'vnpay' | 'momo'] : ''}, quá ${dinhDangNgay(don.han_thanh_toan, 'ngayGio')} đơn sẽ tự hủy.`}
          action={<Button type="primary" loading={dang} onClick={() => void traTien()}>Thanh toán ngay</Button>}
        />
      )}
      {duLieu.co_the_xac_nhan && (
        <Form
          form={form}
          layout="vertical"
          onFinish={(v) => void gui(v)}
          initialValues={{ hinh_thuc_nhan: 'giao_tan_noi', phuong_thuc_tt: 'cod', ten_nguoi_nhan: don.ten_nguoi_nhan, sdt_nguoi_nhan: don.sdt_nguoi_nhan }}
        >
          <Form.Item name="hinh_thuc_nhan" label="Cách nhận hàng">
            <Radio.Group
              options={[
                { value: 'giao_tan_noi', label: 'Giao tận nơi' },
                { value: 'nhan_tai_nha_thuoc', label: 'Nhận tại nhà thuốc' },
              ]}
            />
          </Form.Item>
          {hinhThuc === 'giao_tan_noi' && thanhVien && (soDiaChi.data?.length ?? 0) > 0 && (
            <Form.Item name="dia_chi_id" label="Địa chỉ trong sổ của bạn">
              <Select
                allowClear
                placeholder="Chọn địa chỉ hoặc nhập địa chỉ mới bên dưới"
                options={(soDiaChi.data ?? []).map((d) => ({ value: d.id, label: `${d.ten_nguoi_nhan} · ${d.dia_chi_chi_tiet}, ${d.ten_phuong_xa ?? ''}, ${d.ten_tinh ?? ''}` }))}
              />
            </Form.Item>
          )}
          {hinhThuc === 'giao_tan_noi' && !diaChiId && (
            <>
              <Form.Item name="ten_nguoi_nhan" label="Người nhận" rules={[{ required: true, message: 'Nhập tên người nhận' }]}><Input maxLength={150} /></Form.Item>
              <Form.Item
                name="sdt_nguoi_nhan"
                label="Số điện thoại người nhận"
                rules={[{ validator: (_, v: string) => (v && chuanHoaSdt(v) ? Promise.resolve() : Promise.reject(new Error('Số điện thoại không hợp lệ'))) }]}
              ><Input inputMode="tel" /></Form.Item>
              <Form.Item name="dia_chi_chi_tiet" label="Địa chỉ" rules={[{ required: true, min: 5, message: 'Nhập địa chỉ (số nhà, đường)' }]}><Input maxLength={300} /></Form.Item>
              <Space wrap style={{ width: '100%' }}>
                <Form.Item name="ma_tinh" label="Tỉnh/thành" rules={[{ required: true, message: 'Chọn tỉnh/thành' }]}>
                  <Select
                    showSearch={{ optionFilterProp: 'label' }}
                    style={{ width: 220 }}
                    loading={tinh.isLoading}
                    options={(tinh.data ?? []).map((t) => ({ value: t.ma, label: t.ten }))}
                    onChange={() => form.setFieldValue('ma_phuong_xa', undefined)}
                  />
                </Form.Item>
                <Form.Item name="ma_phuong_xa" label="Phường/xã" rules={[{ required: true, message: 'Chọn phường/xã' }]}>
                  <Select showSearch={{ optionFilterProp: 'label' }} style={{ width: 240 }} disabled={!maTinh} loading={xa.isLoading} options={(xa.data ?? []).map((t) => ({ value: t.ma, label: t.ten }))} />
                </Form.Item>
              </Space>
            </>
          )}
          <Form.Item name="phuong_thuc_tt" label="Thanh toán">
            <Radio.Group
              options={(['cod', 'vnpay', 'momo'] as const).map((k) => ({ value: k, label: NHAN_PHUONG_THUC[k] }))}
            />
          </Form.Item>
          <Form.Item name="ghi_chu" label="Ghi chú thêm"><Input.TextArea rows={2} maxLength={500} /></Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={dang}>Xác nhận đơn</Button>
            <Button danger onClick={xacNhanTuChoi}>Từ chối</Button>
          </Space>
        </Form>
      )}
      {!duLieu.co_the_xac_nhan && !duLieu.co_the_thanh_toan && (
        <Typography.Paragraph type="secondary">Đơn này không còn cần bạn xác nhận.</Typography.Paragraph>
      )}
    </Space>
  )
}
