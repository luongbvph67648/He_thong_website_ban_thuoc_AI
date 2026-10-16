import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Drawer, Form, Image, Input, Space, Spin, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { NHAN_HUONG_XU_LY, NHAN_LY_DO_DOI_TRA, NHAN_TRANG_THAI_DOI_TRA } from '../../../lib/doiTra'
import { usePhien } from '../../../stores/phien'

type Tom = components['schemas']['DoiTraTom']
type TaiKhoan = components['schemas']['TaiKhoanNhanHoanVao']

/** KTV09: yêu cầu đổi trả của tôi, mã vận đơn trả hàng, tài khoản nhận hoàn (đơn COD/tiền mặt). */
export default function TrangDoiTraCuaToi() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const khach = usePhien((s) => s.loai === 'khach')
  const [xem, setXem] = useState<string | null>(null)
  const [form] = Form.useForm<TaiKhoan>()

  const ds = useQuery({
    queryKey: ['doi-tra', 'ds'],
    enabled: khach,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/toi/doi-tra')
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
  })
  const ct = useQuery({
    queryKey: ['doi-tra', 'ct', xem],
    enabled: !!xem,
    gcTime: 0, // URL ký có hạn
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/toi/doi-tra/{ma_yeu_cau}', { params: { path: { ma_yeu_cau: xem! } } })
      if (error || !data) throw error ?? new Error('Không tải được chi tiết')
      return data
    },
  })
  const luuTk = useMutation({
    mutationFn: async (v: TaiKhoan) => {
      const r = await goi(() => api.PUT('/api/v1/toi/doi-tra/{ma_yeu_cau}/tai-khoan-nhan-hoan', { params: { path: { ma_yeu_cau: xem! } }, body: v }))
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
    },
    onSuccess: async () => {
      form.resetFields()
      await qc.invalidateQueries({ queryKey: ['doi-tra'] })
      void message.success('Đã lưu tài khoản nhận hoàn tiền')
    },
    onError: (e: Error) => void message.error(e.message),
  })

  if (!daKhoiPhuc) return <Spin />
  if (!khach) return <Navigate to="/dang-nhap?tiep=/tai-khoan/doi-tra" replace />
  const d = ct.data
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Đổi trả của tôi</Typography.Title>
      <Typography.Text type="secondary">Gửi yêu cầu đổi trả từ trang chi tiết của đơn đã giao.</Typography.Text>
      {ds.isError && <Alert type="error" showIcon title="Không tải được danh sách đổi trả" />}
      <Table<Tom>
        rowKey="ma_yeu_cau"
        loading={ds.isLoading}
        dataSource={ds.data ?? []}
        pagination={false}
        locale={{ emptyText: 'Bạn chưa có yêu cầu đổi trả nào' }}
        columns={[
          { title: 'Mã', dataIndex: 'ma_yeu_cau' },
          { title: 'Đơn', dataIndex: 'ma_don', render: (m: string) => <Link to={`/tai-khoan/don-hang/${m}`}>{m}</Link> },
          { title: 'Lý do', dataIndex: 'ly_do', render: (v: Tom['ly_do']) => NHAN_LY_DO_DOI_TRA[v] },
          { title: 'Gửi lúc', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          { title: 'Trạng thái', dataIndex: 'trang_thai', render: (t: Tom['trang_thai']) => <Tag color={NHAN_TRANG_THAI_DOI_TRA[t].mau}>{NHAN_TRANG_THAI_DOI_TRA[t].nhan}</Tag> },
          { title: '', render: (_, r) => <Button type="link" onClick={() => setXem(r.ma_yeu_cau)}>Chi tiết</Button> },
        ]}
      />
      <Drawer title={`Yêu cầu ${xem ?? ''}`} open={!!xem} onClose={() => setXem(null)} size="large">
        {ct.isLoading && <Spin />}
        {d && (
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <Tag color={NHAN_TRANG_THAI_DOI_TRA[d.trang_thai].mau}>{NHAN_TRANG_THAI_DOI_TRA[d.trang_thai].nhan}</Tag>
            {d.ly_do_tu_choi && <Alert type="warning" showIcon title={`Lý do từ chối: ${d.ly_do_tu_choi}`} />}
            {d.ma_van_don && <Alert type="info" showIcon title={`Mã vận đơn trả hàng: ${d.ma_van_don}`} description="Đóng gói hàng và gửi theo mã vận đơn này." />}
            <Descriptions
              size="small"
              column={1}
              bordered
              items={[
                { key: 'ld', label: 'Lý do', children: NHAN_LY_DO_DOI_TRA[d.ly_do] },
                ...(d.mo_ta ? [{ key: 'mt', label: 'Mô tả', children: d.mo_ta }] : []),
                ...(d.huong_xu_ly ? [{ key: 'hx', label: 'Hướng xử lý', children: NHAN_HUONG_XU_LY[d.huong_xu_ly] }] : []),
                ...(d.huong_xu_ly === 'hoan_tien' && d.so_tien_hoan ? [{ key: 'st', label: 'Số tiền hoàn', children: dinhDangTien(d.so_tien_hoan) }] : []),
              ]}
            />
            <Table
              size="small"
              pagination={false}
              rowKey="ct_don_hang_id"
              dataSource={d.dong}
              columns={[
                { title: 'Sản phẩm', render: (_, r) => `${r.ten_san_pham} (${r.ten_don_vi})` },
                { title: 'Trả', align: 'right', render: (_, r) => `${r.so_luong_tra}/${r.so_luong_mua}` },
                { title: 'Giá trị', align: 'right', render: (_, r) => dinhDangTien(r.thanh_tien) },
              ]}
            />
            <Image.PreviewGroup>
              <Space wrap>{d.anh.filter((u) => !u.includes('.mp4')).map((u) => <Image key={u} src={u} width={120} alt="Bằng chứng đổi trả" />)}</Space>
            </Image.PreviewGroup>
            {d.can_nhap_tai_khoan_hoan && (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Alert
                  type={d.da_nhap_tai_khoan_hoan ? 'success' : 'warning'}
                  showIcon
                  title={d.da_nhap_tai_khoan_hoan ? 'Đã nhận tài khoản. Bạn có thể nhập lại để thay đổi.' : 'Vui lòng nhập tài khoản nhận hoàn tiền'}
                />
                <Form form={form} layout="vertical" onFinish={(v) => luuTk.mutate(v)}>
                  <Form.Item name="ngan_hang" label="Ngân hàng" rules={[{ required: true, message: 'Nhập tên ngân hàng' }]}><Input maxLength={100} /></Form.Item>
                  <Form.Item name="so_tai_khoan" label="Số tài khoản" rules={[{ required: true, pattern: /^[0-9A-Za-z]{6,30}$/, message: 'Số tài khoản 6-30 ký tự chữ hoặc số' }]}><Input maxLength={30} /></Form.Item>
                  <Form.Item name="chu_tai_khoan" label="Chủ tài khoản" rules={[{ required: true, message: 'Nhập tên chủ tài khoản' }]}><Input maxLength={150} /></Form.Item>
                  <Button type="primary" htmlType="submit" loading={luuTk.isPending}>Lưu tài khoản</Button>
                </Form>
              </Space>
            )}
          </Space>
        )}
      </Drawer>
    </Space>
  )
}
