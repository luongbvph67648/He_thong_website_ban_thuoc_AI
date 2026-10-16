import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Modal, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'

type Lenh = components['schemas']['LenhTomTat']

/** KHO12: kho xem các lô bị thu hồi cần gom, rồi lập phiếu hủy hoặc xuất trả NCC ở màn phiếu tương ứng. */
export default function TrangThucHienThuHoi() {
  const [xem, setXem] = useState<number | null>(null)
  const ds = useQuery({ queryKey: ['noi-bo', 'thu-hoi', 'kho', 'ds'], queryFn: async () => { const { data, error } = await api.GET('/api/v1/noi-bo/thu-hoi/thuc-hien'); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  const ct = useQuery({ queryKey: ['noi-bo', 'thu-hoi', 'kho', 'ct', xem], enabled: xem !== null, queryFn: async () => { const { data, error } = await api.GET('/api/v1/noi-bo/thu-hoi/thuc-hien/{lenh_id}', { params: { path: { lenh_id: xem! } } }); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  const d = ct.data
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Thực hiện thu hồi</Typography.Title>
      <Table<Lenh> rowKey="id" size="small" pagination={false} loading={ds.isLoading} dataSource={ds.data?.du_lieu ?? []} locale={{ emptyText: 'Không có lệnh thu hồi nào đang mở' }}
        columns={[
          { title: 'Mã lệnh', dataIndex: 'ma_lenh' }, { title: 'Sản phẩm', dataIndex: 'san_pham_ten' },
          { title: 'Lô', dataIndex: 'so_lo', render: (v: string | null) => v ?? 'Mọi lô' },
          { title: 'Mức độ', dataIndex: 'muc_do', render: (v: string | null) => v && <Tag color="red">{v}</Tag> },
          { title: 'Tạo lúc', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          { title: '', render: (_, r) => <Button type="link" onClick={() => setXem(r.id)}>Xem lô cần gom</Button> },
        ]} />
      <Modal title={d ? `Lệnh ${d.ma_lenh}: ${d.san_pham_ten}` : 'Lệnh thu hồi'} open={xem !== null} onCancel={() => setXem(null)} footer={null} width={720}>
        {d && (
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Alert type="info" showIcon title={<span>Gom hàng tồn và hàng khách trả, rồi lập <Link to="/nhan-vien/phieu-huy">phiếu hủy</Link> hoặc <Link to="/nhan-vien/xuat-tra">phiếu xuất trả NCC</Link> (chờ Admin duyệt). Lệnh đóng được khi các lô về 0.</span>} />
            <Table size="small" pagination={false} rowKey="lo_id" dataSource={d.lo} columns={[
              { title: 'Lô', dataIndex: 'so_lo' }, { title: 'HSD', dataIndex: 'han_su_dung', render: (v: string) => dinhDangNgay(v, 'ngay') },
              { title: 'Tồn bán', dataIndex: 'so_luong_ton', align: 'right' }, { title: 'Biệt trữ', dataIndex: 'so_luong_biet_tru', align: 'right' }, { title: 'Đã bán ra', dataIndex: 'so_luong_da_ban', align: 'right' },
            ]} />
            <Typography.Text strong>Còn phải xử lý: {d.ton_con_lai}</Typography.Text>
          </Space>
        )}
      </Modal>
    </Space>
  )
}
