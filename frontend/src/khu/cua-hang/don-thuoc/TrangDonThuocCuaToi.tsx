import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Drawer, Image, Popconfirm, Space, Spin, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { usePhien } from '../../../stores/phien'

type Tom = components['schemas']['YeuCauDonThuocTom']
type TrangThai = Tom['trang_thai']

const NHAN: Record<TrangThai, { nhan: string; mau: string }> = {
  cho_duyet: { nhan: 'Chờ duyệt', mau: 'gold' },
  dang_tu_van: { nhan: 'Đang tư vấn', mau: 'blue' },
  da_tao_don: { nhan: 'Đã tạo đơn hàng', mau: 'green' },
  tu_choi: { nhan: 'Từ chối', mau: 'red' },
  khach_huy: { nhan: 'Khách hủy', mau: 'default' },
}
const KHOA = ['toi', 'don-thuoc'] as const
const HUY_DUOC = (t: TrangThai) => t === 'cho_duyet' || t === 'dang_tu_van'

/** KTV07: danh sách và trạng thái yêu cầu đơn thuốc của tôi; xem ảnh (URL ký 10 phút), hủy khi còn chờ. */
export default function TrangDonThuocCuaToi() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const khach = usePhien((s) => s.loai === 'khach')
  const [xem, setXem] = useState<string | null>(null)

  const ds = useQuery({
    queryKey: KHOA,
    enabled: khach,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/toi/don-thuoc')
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
  })
  const chiTiet = useQuery({
    queryKey: [...KHOA, xem],
    enabled: !!xem,
    gcTime: 0, // URL ký có hạn: không giữ lại bản cũ
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/toi/don-thuoc/{ma_yeu_cau}', { params: { path: { ma_yeu_cau: xem! } } })
      if (error || !data) throw error ?? new Error('Không tải được chi tiết')
      return data
    },
  })
  const huy = useMutation({
    mutationFn: async (ma: string) => {
      const kq = await goi(() => api.POST('/api/v1/toi/don-thuoc/{ma_yeu_cau}/huy', { params: { path: { ma_yeu_cau: ma } } }))
      if (!kq.ok) throw new Error(thongDiepChung(kq.loi))
    },
    onSuccess: async () => {
      setXem(null)
      await qc.invalidateQueries({ queryKey: KHOA })
      void message.success('Đã hủy yêu cầu')
    },
    onError: (e: Error) => void message.error(e.message),
  })

  if (!daKhoiPhuc) return <Spin />
  if (!khach) return <Navigate to="/dang-nhap?tiep=/tai-khoan/don-thuoc" replace />
  const d = chiTiet.data
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Đơn thuốc của tôi</Typography.Title>
      <Link to="/gui-don-thuoc">Gửi đơn thuốc mới</Link>
      {ds.isError && <Alert type="error" showIcon title="Không tải được danh sách đơn thuốc" />}
      <Table<Tom>
        rowKey="ma_yeu_cau"
        loading={ds.isLoading}
        dataSource={ds.data ?? []}
        pagination={false}
        locale={{ emptyText: 'Bạn chưa gửi đơn thuốc nào' }}
        columns={[
          { title: 'Mã', dataIndex: 'ma_yeu_cau' },
          { title: 'Ngày gửi', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          { title: 'Trạng thái', dataIndex: 'trang_thai', render: (t: TrangThai) => <Tag color={NHAN[t].mau}>{NHAN[t].nhan}</Tag> },
          {
            title: 'Đơn hàng',
            dataIndex: 'ma_don',
            render: (m: string | null) => (m ? <Link to={`/tai-khoan/don-hang/${m}`}>{m}</Link> : '-'),
          },
          { title: '', render: (_, r) => <Button type="link" onClick={() => setXem(r.ma_yeu_cau)}>Chi tiết</Button> },
        ]}
      />
      <Drawer title={`Yêu cầu ${xem ?? ''}`} open={!!xem} onClose={() => setXem(null)} size="large">
        {chiTiet.isLoading && <Spin />}
        {d && (
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <Tag color={NHAN[d.trang_thai].mau}>{NHAN[d.trang_thai].nhan}</Tag>
            {d.ly_do_tu_choi && <Alert type="warning" showIcon title={`Lý do từ chối: ${d.ly_do_tu_choi}`} />}
            {d.ghi_chu && <Typography.Paragraph>Ghi chú: {d.ghi_chu}</Typography.Paragraph>}
            <Image.PreviewGroup>
              <Space wrap>{d.anh.map((u) => <Image key={u} src={u} width={160} alt="Ảnh đơn thuốc" />)}</Space>
            </Image.PreviewGroup>
            {d.ma_don && <Link to={`/tai-khoan/don-hang/${d.ma_don}`}>Xem đơn hàng {d.ma_don}</Link>}
            {HUY_DUOC(d.trang_thai) && (
              <Popconfirm title="Hủy yêu cầu này?" okText="Hủy yêu cầu" cancelText="Không" onConfirm={() => huy.mutate(d.ma_yeu_cau)}>
                <Button danger loading={huy.isPending}>Hủy yêu cầu</Button>
              </Popconfirm>
            )}
          </Space>
        )}
      </Drawer>
    </Space>
  )
}
