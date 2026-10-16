import { useQuery } from '@tanstack/react-query'
import { Button, Descriptions, Result, Spin, Table, Typography } from 'antd'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { NHAN_PHUONG_THUC } from './thanhToan'

/**
 * Kết quả đặt hàng (KTV02) tại `/thanh-toan/ket-qua?ma=...`: trạng thái luôn đọc lại từ máy chủ, không tin tham số URL
 * ngoài mã đơn. Kết quả cổng thanh toán (KTV03) dùng cùng trang ở T4.5.
 */
export default function TrangKetQuaDatHang() {
  const [tham] = useSearchParams()
  const ma = tham.get('ma') ?? ''
  const q = useQuery({
    queryKey: ['don-hang', ma],
    enabled: ma !== '',
    retry: false,
    queryFn: async () => (await api.GET('/api/v1/toi/don-hang/{ma_don}', { params: { path: { ma_don: ma } } })).data ?? null,
  })
  if (ma === '' || (!q.isLoading && !q.data)) {
    return <Result status="404" title="Không tìm thấy đơn hàng" extra={<Link to="/"><Button type="primary">Về trang chủ</Button></Link>} />
  }
  if (q.isLoading || !q.data) return <Spin />
  const don = q.data
  const choThanhToan = don.trang_thai === 'cho_thanh_toan'
  return (
    <>
      <Result
        status={choThanhToan ? 'info' : 'success'}
        title={choThanhToan ? 'Đơn hàng đang chờ thanh toán' : 'Đặt hàng thành công'}
        subTitle={
          choThanhToan
            ? `Vui lòng thanh toán trước ${dinhDangNgay(don.han_thanh_toan, 'ngayGio')}, quá hạn đơn sẽ tự hủy.`
            : 'Nhà thuốc sẽ sớm xác nhận đơn của bạn.'
        }
        extra={<Link to="/"><Button type="primary">Tiếp tục mua sắm</Button></Link>}
      />
      <Typography.Title level={4}>Đơn {don.ma_don}</Typography.Title>
      <Descriptions
        bordered
        size="small"
        column={1}
        items={[
          { key: 'pt', label: 'Thanh toán', children: don.phuong_thuc_tt ? NHAN_PHUONG_THUC[don.phuong_thuc_tt as 'cod' | 'vnpay' | 'momo'] : '—' },
          { key: 'nhan', label: 'Nhận hàng', children: don.dia_chi_giao ? `${don.ten_nguoi_nhan} · ${don.sdt_nguoi_nhan} · ${don.dia_chi_giao}` : 'Nhận tại nhà thuốc' },
          { key: 'tt', label: 'Tạm tính', children: dinhDangTien(don.tam_tinh) },
          { key: 'gg', label: 'Giảm giá', children: `− ${dinhDangTien(don.giam_gia)}` },
          { key: 'ship', label: 'Phí vận chuyển', children: dinhDangTien(don.phi_van_chuyen) },
          { key: 'tong', label: 'Tổng cộng', children: <b>{dinhDangTien(don.tong_tien)}</b> },
        ]}
      />
      <Table
        style={{ marginTop: 16 }}
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
    </>
  )
}
