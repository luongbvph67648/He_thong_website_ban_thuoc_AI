import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Form, Input, Modal, Select, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'

type Lenh = components['schemas']['LenhTomTat']
type ChiTiet = components['schemas']['LenhChiTiet']

function FormTao({ dong }: { dong: () => void }) {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [form] = Form.useForm<{ san_pham_id: number; lo_id?: number; can_cu: string; muc_do?: string }>()
  const [tuKhoa, setTuKhoa] = useState('')
  const [spId, setSpId] = useState<number | undefined>()
  const [loi, setLoi] = useState<string | null>(null)
  const sp = useQuery({ queryKey: ['quan-tri', 'thu-hoi', 'sp', tuKhoa], queryFn: async () => (await api.GET('/api/v1/noi-bo/san-pham', { params: { query: { q: tuKhoa || undefined, kich_thuoc: 20 } } })).data?.du_lieu ?? [] })
  const lo = useQuery({ queryKey: ['quan-tri', 'thu-hoi', 'lo', spId], enabled: spId !== undefined, queryFn: async () => (await api.GET('/api/v1/noi-bo/ton-kho/{san_pham_id}/lo', { params: { path: { san_pham_id: spId! } } })).data ?? [] })
  const tao = useMutation({
    mutationFn: async (v: { san_pham_id: number; lo_id?: number; can_cu: string; muc_do?: string }) => {
      const r = await goi(() => api.POST('/api/v1/noi-bo/thu-hoi', { body: v }))
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
    },
    onSuccess: () => { void message.success('Đã tạo lệnh thu hồi, lô đã bị khóa'); void qc.invalidateQueries({ queryKey: ['quan-tri', 'thu-hoi'] }); dong() },
    onError: (e: Error) => setLoi(e.message),
  })
  return (
    <Modal title="Khởi tạo lệnh thu hồi" open onCancel={dong} okText="Thu hồi" okButtonProps={{ danger: true, loading: tao.isPending }} cancelText="Đóng" onOk={() => form.submit()} destroyOnHidden>
      {loi && <Alert type="error" showIcon title={loi} style={{ marginBottom: 12 }} />}
      <Alert type="warning" showIcon style={{ marginBottom: 12 }} title="Lô bị khóa ngay, gỡ khỏi đơn chưa xuất và thông báo cho khách đã mua." />
      <Form form={form} layout="vertical" onFinish={(v) => tao.mutate(v)}>
        <Form.Item name="san_pham_id" label="Sản phẩm" rules={[{ required: true, message: 'Chọn sản phẩm' }]}>
          <Select showSearch filterOption={false} onSearch={setTuKhoa} onChange={(v: number) => { setSpId(v); form.setFieldValue('lo_id', undefined) }} placeholder="Tìm sản phẩm" options={(sp.data ?? []).map((s) => ({ value: s.id, label: `${s.ten} (${s.sku})` }))} />
        </Form.Item>
        <Form.Item name="lo_id" label="Lô (bỏ trống = mọi lô của sản phẩm)">
          <Select allowClear disabled={spId === undefined} placeholder="Mọi lô" options={(lo.data ?? []).map((l) => ({ value: l.lo_id, label: `${l.so_lo} · HSD ${dinhDangNgay(l.han_su_dung, 'ngay')}` }))} />
        </Form.Item>
        <Form.Item name="can_cu" label="Căn cứ (số công văn, thông báo)" rules={[{ required: true, min: 3, message: 'Nhập căn cứ' }]}><Input maxLength={255} /></Form.Item>
        <Form.Item name="muc_do" label="Mức độ"><Input maxLength={50} placeholder="Ví dụ: Cấp độ 1" /></Form.Item>
      </Form>
    </Modal>
  )
}

/** AD13: khởi tạo, theo dõi và đóng lệnh thu hồi lô. */
export default function TrangThuHoi() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [moTao, setMoTao] = useState(false)
  const [xem, setXem] = useState<number | null>(null)
  const ds = useQuery({ queryKey: ['quan-tri', 'thu-hoi', 'ds'], queryFn: async () => { const { data, error } = await api.GET('/api/v1/noi-bo/thu-hoi'); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  const ct = useQuery({ queryKey: ['quan-tri', 'thu-hoi', 'ct', xem], enabled: xem !== null, queryFn: async () => { const { data, error } = await api.GET('/api/v1/noi-bo/thu-hoi/{lenh_id}', { params: { path: { lenh_id: xem! } } }); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  const dong = useMutation({
    mutationFn: async (id: number) => { const r = await goi(() => api.POST('/api/v1/noi-bo/thu-hoi/{lenh_id}/dong', { params: { path: { lenh_id: id } } })); if (!r.ok) throw new Error(thongDiepChung(r.loi)) },
    onSuccess: () => { void message.success('Đã đóng lệnh'); void qc.invalidateQueries({ queryKey: ['quan-tri', 'thu-hoi'] }) },
    onError: (e: Error) => void message.error(e.message),
  })
  const d: ChiTiet | undefined = ct.data
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={2} style={{ margin: 0 }}>Thu hồi lô</Typography.Title>
        <YeuCauQuyen ma="recall.create" kieu="nut"><Button danger type="primary" onClick={() => setMoTao(true)}>Khởi tạo lệnh thu hồi</Button></YeuCauQuyen>
      </Space>
      <Table<Lenh> rowKey="id" size="small" pagination={false} loading={ds.isLoading} dataSource={ds.data?.du_lieu ?? []} locale={{ emptyText: 'Chưa có lệnh thu hồi' }}
        columns={[
          { title: 'Mã lệnh', dataIndex: 'ma_lenh' },
          { title: 'Sản phẩm', dataIndex: 'san_pham_ten' },
          { title: 'Lô', dataIndex: 'so_lo', render: (v: string | null) => v ?? 'Mọi lô' },
          { title: 'Căn cứ', dataIndex: 'can_cu' },
          { title: 'Khách đã xử lý', render: (_, r) => `${r.so_khach_da_xu_ly}/${r.so_khach}` },
          { title: 'Trạng thái', dataIndex: 'trang_thai', render: (v: Lenh['trang_thai']) => <Tag color={v === 'hoan_tat' ? 'green' : 'red'}>{v === 'hoan_tat' ? 'Đã đóng' : 'Đang thu hồi'}</Tag> },
          { title: 'Tạo lúc', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          { title: '', render: (_, r) => <Button type="link" onClick={() => setXem(r.id)}>Chi tiết</Button> },
        ]} />
      <Modal title={d ? `Lệnh ${d.ma_lenh}` : 'Lệnh thu hồi'} open={xem !== null} onCancel={() => setXem(null)} footer={
        d && d.trang_thai === 'dang_thu_hoi' ? <YeuCauQuyen ma="recall.create" kieu="nut"><Button type="primary" loading={dong.isPending} onClick={() => dong.mutate(d.id)}>Đóng lệnh</Button></YeuCauQuyen> : null
      } width={720}>
        {d && (
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Typography.Text>{d.san_pham_ten} · {d.can_cu}</Typography.Text>
            <Typography.Text>Khách đã xử lý: {d.so_khach_da_xu_ly}/{d.so_khach} · Hàng còn ở lô thu hồi: {d.ton_con_lai}</Typography.Text>
            <Table size="small" pagination={false} rowKey="lo_id" dataSource={d.lo} columns={[
              { title: 'Lô', dataIndex: 'so_lo' }, { title: 'HSD', dataIndex: 'han_su_dung', render: (v: string) => dinhDangNgay(v, 'ngay') },
              { title: 'Tồn bán', dataIndex: 'so_luong_ton', align: 'right' }, { title: 'Biệt trữ', dataIndex: 'so_luong_biet_tru', align: 'right' }, { title: 'Đã bán', dataIndex: 'so_luong_da_ban', align: 'right' },
            ]} />
          </Space>
        )}
      </Modal>
      {moTao && <FormTao dong={() => setMoTao(false)} />}
    </Space>
  )
}
