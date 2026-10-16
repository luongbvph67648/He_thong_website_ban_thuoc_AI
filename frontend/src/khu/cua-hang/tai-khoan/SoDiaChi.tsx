import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { laLoiApi, loiTheoTruong } from '../../../api/loi'
import type { components } from '../../../api/schema'

type DiaChi = components['schemas']['DiaChiRa']
interface FormDiaChi {
  ten_nguoi_nhan: string
  so_dien_thoai: string
  dia_chi_chi_tiet: string
  ma_tinh: string
  ma_phuong_xa: string
  la_mac_dinh?: boolean
}
const KHOA = ['toi', 'dia-chi'] as const
const TOI_DA = 10

/** KTV01: sổ địa chỉ nhận hàng. Mã tỉnh/xã theo danh mục của đơn vị vận chuyển (tên do máy chủ điền). */
export default function SoDiaChi() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [form] = Form.useForm<FormDiaChi>()
  const [dangSua, setDangSua] = useState<DiaChi | 'moi' | null>(null)
  const maTinh = Form.useWatch('ma_tinh', form)

  const ds = useQuery({
    queryKey: KHOA,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/toi/dia-chi')
      if (error || !data) throw error ?? new Error('Không tải được sổ địa chỉ')
      return data
    },
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

  const luu = useMutation({
    mutationFn: async (v: FormDiaChi) => {
      const { la_mac_dinh, ...gui } = v
      const r =
        dangSua !== null && dangSua !== 'moi'
          ? await api.PUT('/api/v1/toi/dia-chi/{dia_chi_id}', { params: { path: { dia_chi_id: dangSua.id } }, body: gui })
          : await api.POST('/api/v1/toi/dia-chi', { body: { ...gui, la_mac_dinh: !!la_mac_dinh } })
      if (r.error) throw r.error
    },
    onSuccess: async () => {
      setDangSua(null)
      await qc.invalidateQueries({ queryKey: KHOA })
      void message.success('Đã lưu địa chỉ')
    },
    onError: (loi) => {
      if (laLoiApi(loi)) {
        const theoTruong = loiTheoTruong(loi)
        if (Object.keys(theoTruong).length > 0) form.setFields(Object.entries(theoTruong).map(([name, e]) => ({ name: name as keyof FormDiaChi, errors: [e] })))
        else void message.error(loi.thong_diep)
      } else void message.error('Không lưu được địa chỉ')
    },
  })
  const viec = useMutation({
    mutationFn: async (f: () => Promise<{ error?: unknown }>) => {
      const r = await f()
      if (r.error) throw r.error
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KHOA }),
    onError: (loi) => void message.error(laLoiApi(loi) ? loi.thong_diep : 'Thao tác thất bại'),
  })

  function mo(dc: DiaChi | 'moi') {
    form.resetFields()
    if (dc !== 'moi') form.setFieldsValue({ ...dc })
    setDangSua(dc)
  }
  const dem = ds.data?.length ?? 0
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>Sổ địa chỉ</Typography.Title>
        <Button type="primary" disabled={dem >= TOI_DA} onClick={() => mo('moi')}>Thêm địa chỉ</Button>
      </Space>
      {ds.isError && <Alert type="error" showIcon message="Không tải được sổ địa chỉ" />}
      {dem === 0 && !ds.isLoading && <Typography.Text type="secondary">Chưa có địa chỉ nào.</Typography.Text>}
      {ds.data?.map((d) => (
        <Card key={d.id} size="small" data-testid="dia-chi">
          <Space orientation="vertical" size={2} style={{ width: '100%' }}>
            <Space>
              <Typography.Text strong>{d.ten_nguoi_nhan}</Typography.Text>
              <span>{d.so_dien_thoai}</span>
              {d.la_mac_dinh && <Tag color="blue">Mặc định</Tag>}
            </Space>
            <span>{[d.dia_chi_chi_tiet, d.ten_phuong_xa, d.ten_tinh].filter(Boolean).join(', ')}</span>
            <Space>
              <Button size="small" onClick={() => mo(d)}>Sửa</Button>
              {!d.la_mac_dinh && (
                <Button size="small" onClick={() => viec.mutate(() => api.POST('/api/v1/toi/dia-chi/{dia_chi_id}/mac-dinh', { params: { path: { dia_chi_id: d.id } } }))}>
                  Đặt làm mặc định
                </Button>
              )}
              <Popconfirm title="Xóa địa chỉ này?" okText="Xóa" cancelText="Hủy" onConfirm={() => viec.mutate(() => api.DELETE('/api/v1/toi/dia-chi/{dia_chi_id}', { params: { path: { dia_chi_id: d.id } } }))}>
                <Button size="small" danger>Xóa</Button>
              </Popconfirm>
            </Space>
          </Space>
        </Card>
      ))}
      <Modal
        open={dangSua !== null}
        title={dangSua === 'moi' ? 'Thêm địa chỉ' : 'Sửa địa chỉ'}
        okText="Lưu"
        cancelText="Hủy"
        confirmLoading={luu.isPending}
        onCancel={() => setDangSua(null)}
        onOk={() => form.submit()}
        mask={{ closable: false }}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={(v) => luu.mutate(v)}>
          <Form.Item name="ten_nguoi_nhan" label="Người nhận" rules={[{ required: true, message: 'Nhập tên người nhận' }]}><Input maxLength={150} /></Form.Item>
          <Form.Item name="so_dien_thoai" label="Số điện thoại" rules={[{ required: true, message: 'Nhập số điện thoại' }]}><Input maxLength={20} /></Form.Item>
          <Form.Item name="ma_tinh" label="Tỉnh/thành phố" rules={[{ required: true, message: 'Chọn tỉnh/thành phố' }]}>
            <Select showSearch optionFilterProp="label" placeholder="Chọn tỉnh/thành phố" options={(tinh.data ?? []).map((t) => ({ value: t.ma, label: t.ten }))} onChange={() => form.setFieldValue('ma_phuong_xa', undefined)} />
          </Form.Item>
          <Form.Item name="ma_phuong_xa" label="Phường/xã" rules={[{ required: true, message: 'Chọn phường/xã' }]}>
            <Select showSearch optionFilterProp="label" placeholder="Chọn phường/xã" disabled={!maTinh} loading={xa.isLoading} options={(xa.data ?? []).map((x) => ({ value: x.ma, label: x.ten }))} />
          </Form.Item>
          <Form.Item name="dia_chi_chi_tiet" label="Số nhà, đường" rules={[{ required: true, min: 5, message: 'Nhập số nhà, tên đường (ít nhất 5 ký tự)' }]}><Input maxLength={300} /></Form.Item>
          {dangSua === 'moi' && <Form.Item name="la_mac_dinh" label="Đặt làm mặc định" valuePropName="checked"><Switch /></Form.Item>}
        </Form>
      </Modal>
    </Space>
  )
}
