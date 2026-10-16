import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Input, Modal, Result, Space, Spin, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { khachHuyDuoc } from '../../../lib/donHang'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { nhanTrangThai } from '../../../lib/trangThai'
import { usePhien } from '../../../stores/phien'
import { NHAN_PHUONG_THUC } from '../gio-hang/thanhToan'
import LichSuTrangThai from './LichSuTrangThai'

/** KTV06: chi tiết đơn của tôi, dòng thời gian trạng thái và nút hủy đơn (chỉ khi chưa sang "Đang soạn hàng"). */
export default function TrangChiTietDonCuaToi() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const { ma = '' } = useParams()
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const khach = usePhien((s) => s.loai === 'khach')
  const [moHuy, setMoHuy] = useState(false)
  const [lyDo, setLyDo] = useState('')
  const [dangHuy, setDangHuy] = useState(false)
  const q = useQuery({
    queryKey: ['don-hang', ma],
    enabled: khach && ma !== '',
    retry: false,
    queryFn: async () => (await api.GET('/api/v1/toi/don-hang/{ma_don}', { params: { path: { ma_don: ma } } })).data ?? null,
  })
  if (!daKhoiPhuc) return <Spin />
  if (!khach) return <Navigate to={`/dang-nhap?tiep=/tai-khoan/don-hang/${ma}`} replace />
  if (q.isLoading) return <Spin />
  const don = q.data
  if (!don) return <Result status="404" title="Không tìm thấy đơn hàng" extra={<Link to="/tai-khoan/don-hang"><Button type="primary">Về danh sách đơn</Button></Link>} />
  const tt = nhanTrangThai('don_hang', don.trang_thai)
  const ttThanhToan = nhanTrangThai('thanh_toan', don.trang_thai_tt)

  async function huy() {
    setDangHuy(true)
    const r = await goi(() => api.POST('/api/v1/toi/don-hang/{ma_don}/huy', { params: { path: { ma_don: ma } }, body: { ly_do: lyDo.trim() || null } }))
    setDangHuy(false)
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    setMoHuy(false)
    void message.success('Đã hủy đơn hàng')
    void queryClient.invalidateQueries({ queryKey: ['don-hang'] })
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Typography.Title level={2} style={{ margin: 0 }}>Đơn {don.ma_don}</Typography.Title>
        <Tag color={tt.mau}>{tt.nhan}</Tag>
        <Tag color={ttThanhToan.mau}>{ttThanhToan.nhan}</Tag>
        {khachHuyDuoc(don.trang_thai) && <Button danger onClick={() => setMoHuy(true)}>Hủy đơn</Button>}
      </Space>
      {don.trang_thai_tt === 'cho_hoan_tien' && (
        <Alert type="info" showIcon message="Nhà thuốc sẽ hoàn lại tiền cho đơn này. Bạn sẽ nhận được thông báo khi hoàn tất." />
      )}
      {don.ly_do_huy && <Alert type="warning" showIcon message={`Lý do hủy: ${don.ly_do_huy}`} />}
      <Descriptions bordered size="small" column={1}>
        <Descriptions.Item label="Ngày đặt">{dinhDangNgay(don.created_at, 'ngayGio')}</Descriptions.Item>
        <Descriptions.Item label="Thanh toán">{don.phuong_thuc_tt ? (NHAN_PHUONG_THUC[don.phuong_thuc_tt as 'cod' | 'vnpay' | 'momo'] ?? don.phuong_thuc_tt) : '—'}</Descriptions.Item>
        <Descriptions.Item label="Người nhận">{[don.ten_nguoi_nhan, don.sdt_nguoi_nhan].filter(Boolean).join(' · ') || '—'}</Descriptions.Item>
        <Descriptions.Item label="Địa chỉ giao">{don.dia_chi_giao ?? 'Nhận tại nhà thuốc'}</Descriptions.Item>
        {don.van_don.length > 0 && <Descriptions.Item label="Mã vận đơn">{don.van_don.map((v) => `${v.don_vi_van_chuyen} ${v.ma_van_don ?? ''}`.trim()).join(', ')}</Descriptions.Item>}
        {don.ghi_chu && <Descriptions.Item label="Ghi chú">{don.ghi_chu}</Descriptions.Item>}
      </Descriptions>
      <Table
        size="small"
        rowKey={(d) => `${d.san_pham_id}-${d.ten_don_vi}`}
        pagination={false}
        dataSource={don.dong}
        columns={[
          { title: 'Sản phẩm', key: 'ten', render: (_, d) => `${d.ten_san_pham} (${d.ten_don_vi})` },
          { title: 'SL', dataIndex: 'so_luong', key: 'sl', align: 'right' },
          { title: 'Đơn giá', key: 'gia', align: 'right', render: (_, d) => dinhDangTien(d.don_gia) },
          { title: 'Thành tiền', key: 'tt', align: 'right', render: (_, d) => dinhDangTien(d.thanh_tien) },
        ]}
        summary={() => (
          <>
            <Table.Summary.Row><Table.Summary.Cell index={0} colSpan={3}>Tạm tính</Table.Summary.Cell><Table.Summary.Cell index={1} align="right">{dinhDangTien(don.tam_tinh)}</Table.Summary.Cell></Table.Summary.Row>
            <Table.Summary.Row><Table.Summary.Cell index={0} colSpan={3}>Giảm giá</Table.Summary.Cell><Table.Summary.Cell index={1} align="right">-{dinhDangTien(don.giam_gia)}</Table.Summary.Cell></Table.Summary.Row>
            <Table.Summary.Row><Table.Summary.Cell index={0} colSpan={3}>Phí vận chuyển</Table.Summary.Cell><Table.Summary.Cell index={1} align="right">{dinhDangTien(don.phi_van_chuyen)}</Table.Summary.Cell></Table.Summary.Row>
            <Table.Summary.Row><Table.Summary.Cell index={0} colSpan={3}><b>Tổng cộng</b></Table.Summary.Cell><Table.Summary.Cell index={1} align="right"><b>{dinhDangTien(don.tong_tien)}</b></Table.Summary.Cell></Table.Summary.Row>
          </>
        )}
      />
      <Typography.Title level={4} style={{ margin: 0 }}>Trạng thái đơn hàng</Typography.Title>
      <LichSuTrangThai moc={don.lich_su} />
      <Modal title="Hủy đơn hàng" open={moHuy} okText="Hủy đơn" okButtonProps={{ danger: true, loading: dangHuy }} cancelText="Giữ đơn" onOk={() => void huy()} onCancel={() => setMoHuy(false)} destroyOnHidden>
        <p>Đơn sẽ bị hủy, hàng giữ được nhả lại. Nếu đã thanh toán online, nhà thuốc sẽ hoàn tiền cho bạn.</p>
        <Input.TextArea rows={3} maxLength={500} placeholder="Lý do hủy (không bắt buộc)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
      </Modal>
    </Space>
  )
}
