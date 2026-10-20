import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Input, Modal, Result, Space, Spin, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { NHAN_PHUONG_THUC_DON, duocSiHuyDuoc, duocSiXacNhanDuoc } from '../../../lib/donHang'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { coQuyen } from '../../../lib/quyen'
import { nhanTrangThai } from '../../../lib/trangThai'
import { usePhien } from '../../../stores/phien'
import LichSuTrangThai from '../../cua-hang/don-hang/LichSuTrangThai'

/** DS01, DS02, DS03: chi tiết đơn nội bộ, dòng thời gian, xác nhận và hủy đơn (nút theo quyền và trạng thái). */
export default function TrangChiTietDon() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const { id = '' } = useParams()
  const quyen = usePhien((s) => s.quyen)
  const [moHuy, setMoHuy] = useState(false)
  const [lyDo, setLyDo] = useState('')
  const [dangGui, setDangGui] = useState(false)
  const idSo = Number(id)
  const q = useQuery({
    queryKey: ['nhan-vien', 'don-hang', 'ct', idSo],
    enabled: Number.isInteger(idSo) && idSo > 0,
    retry: false,
    queryFn: async () => (await api.GET('/api/v1/noi-bo/don-hang/{don_id}', { params: { path: { don_id: idSo } } })).data ?? null,
  })
  if (q.isLoading) return <Spin />
  const don = q.data
  if (!don) return <Result status="404" title="Không tìm thấy đơn hàng" extra={<Link to=".." relative="path"><Button type="primary">Về danh sách đơn</Button></Link>} />
  const tt = nhanTrangThai('don_hang', don.trang_thai)
  const ttTt = nhanTrangThai('thanh_toan', don.trang_thai_tt)

  async function thucHien(thaoTac: () => ReturnType<typeof goiXacNhan>, thanhCong: string) {
    setDangGui(true)
    const r = await thaoTac()
    setDangGui(false)
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    void message.success(thanhCong)
    setMoHuy(false)
    setLyDo('')
    void queryClient.invalidateQueries({ queryKey: ['nhan-vien', 'don-hang'] })
  }
  const goiXacNhan = () => goi(() => api.POST('/api/v1/noi-bo/don-hang/{don_id}/xac-nhan', { params: { path: { don_id: idSo } } }))
  const goiHuy = () => goi(() => api.POST('/api/v1/noi-bo/don-hang/{don_id}/huy', { params: { path: { don_id: idSo } }, body: { ly_do: lyDo.trim() } }))

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Link to=".." relative="path">← Danh sách đơn</Link>
      <Space wrap>
        <Typography.Title level={3} style={{ margin: 0 }}>Đơn {don.ma_don}</Typography.Title>
        <Tag color={tt.mau}>{tt.nhan}</Tag>
        <Tag color={ttTt.mau}>{ttTt.nhan}</Tag>
        {coQuyen(quyen, 'order.confirm') && duocSiXacNhanDuoc(don.trang_thai) && (
          <Button type="primary" loading={dangGui} onClick={() => void thucHien(goiXacNhan, 'Đã xác nhận đơn')}>Xác nhận đơn</Button>
        )}
        {coQuyen(quyen, 'order.cancel') && duocSiHuyDuoc(don.trang_thai) && <Button danger onClick={() => setMoHuy(true)}>Hủy đơn</Button>}
      </Space>
      {don.trang_thai === 'cho_thanh_toan' && (don.phuong_thuc_tt === 'vnpay' || don.phuong_thuc_tt === 'momo') && (
        <Alert
          type="info"
          showIcon
          message={`Đơn đang chờ ${NHAN_PHUONG_THUC_DON[don.phuong_thuc_tt]} xác nhận thanh toán.`}
          description="Dược sĩ có thể xác nhận đơn sau khi cổng thanh toán báo thành công. Mã giao dịch và trạng thái thanh toán được hệ thống đối chiếu tự động."
        />
      )}
      {don.trang_thai === 'cho_xac_nhan' && don.trang_thai_tt === 'da_thanh_toan' && (don.phuong_thuc_tt === 'vnpay' || don.phuong_thuc_tt === 'momo') && (
        <Alert type="success" showIcon message="Thanh toán online đã được hệ thống xác nhận. Dược sĩ có thể xác nhận đơn." />
      )}
      {don.trang_thai_tt === 'cho_hoan_tien' && <Alert type="info" showIcon message="Đơn đã thanh toán: giao dịch hoàn tiền đang chờ Admin xác nhận." />}
      {don.ly_do_huy && <Alert type="warning" showIcon message={`Lý do hủy: ${don.ly_do_huy}`} />}
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="Ngày đặt">{dinhDangNgay(don.created_at, 'ngayGio')}</Descriptions.Item>
        <Descriptions.Item label="Kênh">{nhanTrangThai('kenh_ban', don.kenh_ban).nhan}</Descriptions.Item>
        <Descriptions.Item label="Thanh toán">{don.phuong_thuc_tt ? (NHAN_PHUONG_THUC_DON[don.phuong_thuc_tt] ?? don.phuong_thuc_tt) : '—'}</Descriptions.Item>
        <Descriptions.Item label="Mã giảm giá">{don.ma_giam_gia ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="Người nhận">{[don.ten_nguoi_nhan, don.sdt_nguoi_nhan].filter(Boolean).join(' · ') || '—'}</Descriptions.Item>
        <Descriptions.Item label="Địa chỉ giao">{don.dia_chi_giao ?? 'Nhận tại nhà thuốc'}</Descriptions.Item>
        {don.ghi_chu && <Descriptions.Item label="Ghi chú" span={2}>{don.ghi_chu}</Descriptions.Item>}
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
          { title: 'Giảm', key: 'giam', align: 'right', render: (_, d) => dinhDangTien(d.giam_gia_phan_bo) },
          { title: 'Thành tiền', key: 'tt', align: 'right', render: (_, d) => dinhDangTien(d.thanh_tien) },
        ]}
        footer={() => `Tạm tính ${dinhDangTien(don.tam_tinh)} · Giảm ${dinhDangTien(don.giam_gia)} · Phí vận chuyển ${dinhDangTien(don.phi_van_chuyen)} · Tổng ${dinhDangTien(don.tong_tien)}`}
      />
      {don.giao_dich.length > 0 && (
        <Table
          size="small"
          title={() => 'Giao dịch thanh toán'}
          rowKey="id"
          pagination={false}
          dataSource={don.giao_dich}
          columns={[
            { title: 'Loại', key: 'loai', render: (_, g) => (g.loai === 'hoan_tien' ? 'Hoàn tiền' : 'Thanh toán') },
            { title: 'Cổng', key: 'cong', render: (_, g) => NHAN_PHUONG_THUC_DON[g.cong_thanh_toan] ?? g.cong_thanh_toan },
            { title: 'Số tiền', key: 'tien', align: 'right', render: (_, g) => dinhDangTien(g.so_tien) },
            { title: 'Trạng thái', dataIndex: 'trang_thai', key: 'tt' },
            { title: 'Lúc', key: 'luc', render: (_, g) => dinhDangNgay(g.created_at, 'ngayGio') },
          ]}
        />
      )}
      <Typography.Title level={4} style={{ margin: 0 }}>Dòng thời gian</Typography.Title>
      <LichSuTrangThai moc={don.lich_su} />
      <Modal title="Hủy đơn hàng" open={moHuy} okText="Hủy đơn" okButtonProps={{ danger: true, loading: dangGui, disabled: !lyDo.trim() }} cancelText="Đóng" onOk={() => void thucHien(goiHuy, 'Đã hủy đơn')} onCancel={() => setMoHuy(false)} destroyOnHidden>
        <p>Hàng giữ hoặc đã xuất khỏi kho sẽ được hoàn lại đúng lô; đơn đã thanh toán sẽ tạo giao dịch hoàn tiền chờ Admin xác nhận.</p>
        <Input.TextArea rows={3} maxLength={500} placeholder="Lý do hủy (bắt buộc)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
      </Modal>
    </Space>
  )
}
