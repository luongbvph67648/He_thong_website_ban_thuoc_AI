import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Image, Input, Modal, Rate, Select, Space, Table, Tabs, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'

type DG = components['schemas']['DanhGiaNoiBo']
type HD = components['schemas']['HoiDapNoiBo']

function DanhGiaTab() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [loc, setLoc] = useState<boolean | undefined>()
  const [phanHoi, setPhanHoi] = useState<{ d: DG; nd: string } | null>(null)
  const ds = useQuery({
    queryKey: ['noi-bo', 'kiem-duyet', 'danh-gia', loc],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/kiem-duyet/danh-gia', { params: { query: { dang_hien: loc } } })
      if (error || !data) throw error ?? new Error('Lỗi')
      return data
    },
  })
  const hanhDong = useMutation({
    mutationFn: async (f: () => Promise<{ ok: boolean; loi?: Parameters<typeof thongDiepChung>[0] }>) => {
      const r = await f()
      if (!r.ok) throw new Error(thongDiepChung(r.loi ?? null))
    },
    onSuccess: () => { setPhanHoi(null); void qc.invalidateQueries({ queryKey: ['noi-bo', 'kiem-duyet'] }) },
    onError: (e: Error) => void message.error(e.message),
  })
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Select allowClear placeholder="Tất cả" style={{ width: 200 }} value={loc} onChange={setLoc} options={[{ value: true, label: 'Đang hiện' }, { value: false, label: 'Đã ẩn' }]} />
      <Table<DG> rowKey="id" size="small" pagination={false} loading={ds.isLoading} dataSource={ds.data?.du_lieu ?? []} locale={{ emptyText: 'Không có đánh giá' }}
        columns={[
          { title: 'Sản phẩm', dataIndex: 'san_pham_ten' },
          { title: 'Khách', dataIndex: 'ten_khach' },
          { title: 'Sao', dataIndex: 'so_sao', render: (v: number) => <Rate disabled value={v} style={{ fontSize: 12 }} /> },
          { title: 'Nội dung', render: (_, r) => <Space orientation="vertical" size={4}><span style={{ whiteSpace: 'pre-wrap' }}>{r.noi_dung}</span><Space wrap>{r.anh.map((u) => <Image key={u} src={u} width={40} alt="Ảnh đánh giá" />)}</Space>{r.phan_hoi && <Tag color="blue">Đã phản hồi</Tag>}</Space> },
          { title: 'Ngày', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngay') },
          {
            title: '',
            render: (_, r) => (
              <Space>
                <Button size="small" onClick={() => hanhDong.mutate(() => goi(() => api.PUT('/api/v1/noi-bo/kiem-duyet/danh-gia/{dg_id}/hien-thi', { params: { path: { dg_id: r.id } }, body: { dang_hien: !r.dang_hien } })))}>{r.dang_hien ? 'Ẩn' : 'Hiện lại'}</Button>
                <Button size="small" onClick={() => setPhanHoi({ d: r, nd: r.phan_hoi ?? '' })}>Phản hồi</Button>
              </Space>
            ),
          },
        ]} />
      <Modal title="Phản hồi đánh giá" open={phanHoi !== null} onCancel={() => setPhanHoi(null)} okText="Lưu phản hồi" cancelText="Đóng" okButtonProps={{ disabled: (phanHoi?.nd.trim().length ?? 0) < 2 }}
        onOk={() => phanHoi && hanhDong.mutate(() => goi(() => api.PUT('/api/v1/noi-bo/kiem-duyet/danh-gia/{dg_id}/phan-hoi', { params: { path: { dg_id: phanHoi.d.id } }, body: { phan_hoi: phanHoi.nd.trim() } })))}>
        <Input.TextArea aria-label="Nội dung phản hồi" rows={4} maxLength={2000} value={phanHoi?.nd} onChange={(e) => setPhanHoi((p) => p && { ...p, nd: e.target.value })} />
      </Modal>
    </Space>
  )
}

function HoiDapTab() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [chuaTraLoi, setChuaTraLoi] = useState<boolean | undefined>(true)
  const [tl, setTl] = useState<{ h: HD; nd: string } | null>(null)
  const ds = useQuery({
    queryKey: ['noi-bo', 'kiem-duyet', 'hoi-dap', chuaTraLoi],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/kiem-duyet/hoi-dap', { params: { query: { chua_tra_loi: chuaTraLoi } } })
      if (error || !data) throw error ?? new Error('Lỗi')
      return data
    },
  })
  const hanhDong = useMutation({
    mutationFn: async (f: () => Promise<{ ok: boolean; loi?: Parameters<typeof thongDiepChung>[0] }>) => {
      const r = await f()
      if (!r.ok) throw new Error(thongDiepChung(r.loi ?? null))
    },
    onSuccess: () => { setTl(null); void qc.invalidateQueries({ queryKey: ['noi-bo', 'kiem-duyet'] }) },
    onError: (e: Error) => void message.error(e.message),
  })
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Select allowClear placeholder="Tất cả" style={{ width: 220 }} value={chuaTraLoi} onChange={setChuaTraLoi} options={[{ value: true, label: 'Chưa trả lời' }, { value: false, label: 'Đã trả lời' }]} />
      <Table<HD> rowKey="id" size="small" pagination={false} loading={ds.isLoading} dataSource={ds.data?.du_lieu ?? []} locale={{ emptyText: 'Không có câu hỏi' }}
        columns={[
          { title: 'Sản phẩm', dataIndex: 'san_pham_ten' },
          { title: 'Khách', dataIndex: 'ten_khach' },
          { title: 'Câu hỏi', render: (_, r) => <Space orientation="vertical" size={4}><span style={{ whiteSpace: 'pre-wrap' }}>{r.cau_hoi}</span>{r.tra_loi && <Typography.Text type="secondary">Trả lời: {r.tra_loi}</Typography.Text>}{!r.dang_hien && <Tag>Đã ẩn</Tag>}</Space> },
          { title: 'Ngày', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngay') },
          {
            title: '',
            render: (_, r) => (
              <Space>
                <Button size="small" type="primary" onClick={() => setTl({ h: r, nd: r.tra_loi ?? '' })}>{r.tra_loi ? 'Sửa trả lời' : 'Trả lời'}</Button>
                <Button size="small" onClick={() => hanhDong.mutate(() => goi(() => api.PUT('/api/v1/noi-bo/kiem-duyet/hoi-dap/{hoi_id}/hien-thi', { params: { path: { hoi_id: r.id } }, body: { dang_hien: !r.dang_hien } })))}>{r.dang_hien ? 'Ẩn' : 'Hiện lại'}</Button>
              </Space>
            ),
          },
        ]} />
      <Modal title="Trả lời câu hỏi" open={tl !== null} onCancel={() => setTl(null)} okText="Gửi trả lời" cancelText="Đóng" okButtonProps={{ disabled: (tl?.nd.trim().length ?? 0) < 2 }}
        onOk={() => tl && hanhDong.mutate(() => goi(() => api.POST('/api/v1/noi-bo/kiem-duyet/hoi-dap/{hoi_id}/tra-loi', { params: { path: { hoi_id: tl.h.id } }, body: { tra_loi: tl.nd.trim() } })))}>
        <Typography.Paragraph>{tl?.h.cau_hoi}</Typography.Paragraph>
        <Input.TextArea aria-label="Nội dung trả lời" rows={4} maxLength={2000} value={tl?.nd} onChange={(e) => setTl((p) => p && { ...p, nd: e.target.value })} />
      </Modal>
    </Space>
  )
}

/** DS11: kiểm duyệt đánh giá và trả lời hỏi đáp. */
export default function TrangKiemDuyet() {
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Kiểm duyệt đánh giá và hỏi đáp</Typography.Title>
      <Tabs items={[{ key: 'dg', label: 'Đánh giá', children: <DanhGiaTab /> }, { key: 'hd', label: 'Hỏi đáp', children: <HoiDapTab /> }]} />
    </Space>
  )
}
