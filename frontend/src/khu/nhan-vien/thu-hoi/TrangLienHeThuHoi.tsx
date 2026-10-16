import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'

type Lenh = components['schemas']['LenhTomTat']
type Khach = components['schemas']['KhachThuHoi']
type KetQua = Khach['ket_qua_lien_he']

const NHAN: Record<KetQua, string> = { chua_lien_he: 'Chưa liên hệ', da_lien_he: 'Đã liên hệ', da_hen_tra_hang: 'Đã hẹn trả hàng', da_thu_ve: 'Đã thu về', khong_lien_lac_duoc: 'Không liên lạc được' }

/** DS13: dược sĩ liên hệ khách đã mua lô bị thu hồi và ghi nhận kết quả. */
export default function TrangLienHeThuHoi() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [lenh, setLenh] = useState<Lenh | null>(null)
  const [sua, setSua] = useState<Khach | null>(null)
  const [form] = Form.useForm<{ ket_qua_lien_he: KetQua; so_luong_da_thu_ve?: number; ghi_chu?: string }>()
  const ds = useQuery({ queryKey: ['noi-bo', 'thu-hoi', 'lien-he', 'ds'], queryFn: async () => { const { data, error } = await api.GET('/api/v1/noi-bo/thu-hoi/lien-he'); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  const khach = useQuery({ queryKey: ['noi-bo', 'thu-hoi', 'lien-he', 'khach', lenh?.id], enabled: lenh !== null, queryFn: async () => { const { data, error } = await api.GET('/api/v1/noi-bo/thu-hoi/lien-he/{lenh_id}/khach', { params: { path: { lenh_id: lenh!.id } } }); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  const luu = useMutation({
    mutationFn: async (v: { ket_qua_lien_he: KetQua; so_luong_da_thu_ve?: number; ghi_chu?: string }) => {
      const r = await goi(() => api.PUT('/api/v1/noi-bo/thu-hoi/lien-he/khach/{ct_id}', { params: { path: { ct_id: sua!.id } }, body: v }))
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
    },
    onSuccess: () => { setSua(null); void qc.invalidateQueries({ queryKey: ['noi-bo', 'thu-hoi', 'lien-he'] }) },
    onError: (e: Error) => void message.error(e.message),
  })
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Liên hệ khách thu hồi</Typography.Title>
      <Table<Lenh> rowKey="id" size="small" pagination={false} loading={ds.isLoading} dataSource={ds.data?.du_lieu ?? []} locale={{ emptyText: 'Không có lệnh thu hồi nào đang mở' }}
        columns={[
          { title: 'Mã lệnh', dataIndex: 'ma_lenh' }, { title: 'Sản phẩm', dataIndex: 'san_pham_ten' },
          { title: 'Lô', dataIndex: 'so_lo', render: (v: string | null) => v ?? 'Mọi lô' },
          { title: 'Đã liên hệ', render: (_, r) => `${r.so_khach_da_xu_ly}/${r.so_khach}` },
          { title: '', render: (_, r) => <Button type="link" onClick={() => setLenh(r)}>Danh sách khách</Button> },
        ]} />
      <Modal title={lenh ? `Khách của lệnh ${lenh.ma_lenh}` : ''} open={lenh !== null} onCancel={() => setLenh(null)} footer={null} width={820}>
        <Table<Khach> rowKey="id" size="small" pagination={false} loading={khach.isLoading} dataSource={khach.data ?? []} columns={[
          { title: 'Đơn', dataIndex: 'ma_don' }, { title: 'Khách', dataIndex: 'ten_khach' }, { title: 'SĐT', dataIndex: 'so_dien_thoai' },
          { title: 'Đã mua', dataIndex: 'so_luong_da_ban', align: 'right' }, { title: 'Đã thu về', dataIndex: 'so_luong_da_thu_ve', align: 'right' },
          { title: 'Kết quả', dataIndex: 'ket_qua_lien_he', render: (v: KetQua) => <Tag color={v === 'chua_lien_he' ? 'gold' : 'green'}>{NHAN[v]}</Tag> },
          { title: '', render: (_, r) => <Button size="small" onClick={() => { setSua(r); form.setFieldsValue({ ket_qua_lien_he: r.ket_qua_lien_he, so_luong_da_thu_ve: r.so_luong_da_thu_ve, ghi_chu: r.ghi_chu ?? undefined }) }}>Ghi kết quả</Button> },
        ]} />
      </Modal>
      <Modal title="Kết quả liên hệ" open={sua !== null} onCancel={() => setSua(null)} okText="Lưu" cancelText="Đóng" confirmLoading={luu.isPending} onOk={() => form.submit()} destroyOnHidden forceRender>
        <Form form={form} layout="vertical" onFinish={(v) => luu.mutate(v)}>
          <Form.Item name="ket_qua_lien_he" label="Kết quả" rules={[{ required: true }]}><Select options={(Object.keys(NHAN) as KetQua[]).map((k) => ({ value: k, label: NHAN[k] }))} /></Form.Item>
          <Form.Item name="so_luong_da_thu_ve" label="Số lượng đã thu về (đơn vị cơ sở)"><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="ghi_chu" label="Ghi chú"><Input.TextArea rows={3} maxLength={1000} /></Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
