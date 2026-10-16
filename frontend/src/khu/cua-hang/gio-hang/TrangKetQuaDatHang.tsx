import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Result, Spin, Table, Typography } from 'antd'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { NHAN_PHUONG_THUC } from './thanhToan'
import { chuyenSangCong, layUrlThanhToan } from './thanhToanOnline'

/**
 * Kết quả đặt hàng (KTV02) tại `/thanh-toan/ket-qua?ma=...`: trạng thái luôn đọc lại từ máy chủ, không tin tham số URL
 * ngoài mã đơn. Cũng là nơi cổng thanh toán (KTV03) đưa khách về: đơn còn chờ thanh toán thì hỏi lại mỗi 3 giây (IPN
 * có thể đến sau khi khách được chuyển về) và cho phép thanh toán lại bằng giao dịch mới.
 */
export default function TrangKetQuaDatHang() {
  const { message } = App.useApp()
  const [dangMo, datDangMo] = useState(false)
  const [tham] = useSearchParams()
  const ma = tham.get('ma') ?? ''
  const q = useQuery({
    queryKey: ['don-hang', ma],
    enabled: ma !== '',
    retry: false,
    refetchInterval: (query) => (query.state.data?.trang_thai === 'cho_thanh_toan' ? 3000 : false),
    queryFn: async () => {
      // Khách vãng lai (đơn từ đơn thuốc) vào bằng link mã truy cập: token được lưu lúc bấm thanh toán.
      const token = sessionStorage.getItem(`xacNhanDon:${ma}`)
      if (token) return (await api.GET('/api/v1/xac-nhan-don/{token}', { params: { path: { token } } })).data?.don ?? null
      return (await api.GET('/api/v1/toi/don-hang/{ma_don}', { params: { path: { ma_don: ma } } })).data ?? null
    },
  })
  if (ma === '' || (!q.isLoading && !q.data)) {
    return <Result status="404" title="Không tìm thấy đơn hàng" extra={<Link to="/"><Button type="primary">Về trang chủ</Button></Link>} />
  }
  if (q.isLoading || !q.data) return <Spin />
  const don = q.data
  const choThanhToan = don.trang_thai === 'cho_thanh_toan'
  const daHuy = don.trang_thai === 'da_huy'
  const choHoan = don.trang_thai_tt === 'cho_hoan_tien'

  async function thanhToanLai() {
    datDangMo(true)
    const token = sessionStorage.getItem(`xacNhanDon:${don.ma_don}`)
    const r = token
      ? await goi(() =>
          api.POST('/api/v1/xac-nhan-don/{token}/thanh-toan', { params: { path: { token }, header: { 'Idempotency-Key': crypto.randomUUID() } } }),
        )
      : await layUrlThanhToan(don.ma_don)
    datDangMo(false)
    if (r.ok) chuyenSangCong.di(r.data.url_thanh_toan)
    else void message.error(thongDiepChung(r.loi))
  }

  const dau = daHuy
    ? { status: 'warning' as const, title: 'Đơn hàng đã bị hủy', sub: 'Đơn đã hủy (quá hạn thanh toán hoặc theo yêu cầu), hàng đã được nhả về kho.' }
    : choThanhToan
      ? {
          status: 'info' as const,
          title: 'Đơn hàng đang chờ thanh toán',
          sub: `Vui lòng thanh toán trước ${dinhDangNgay(don.han_thanh_toan, 'ngayGio')}, quá hạn đơn sẽ tự hủy.`,
        }
      : don.trang_thai_tt === 'da_thanh_toan'
        ? { status: 'success' as const, title: 'Thanh toán thành công', sub: 'Nhà thuốc sẽ sớm xác nhận đơn của bạn.' }
        : { status: 'success' as const, title: 'Đặt hàng thành công', sub: 'Nhà thuốc sẽ sớm xác nhận đơn của bạn.' }
  return (
    <>
      <Result
        status={dau.status}
        title={dau.title}
        subTitle={dau.sub}
        extra={[
          choThanhToan && (
            <Button key="tt" type="primary" loading={dangMo} onClick={thanhToanLai}>
              Thanh toán lại
            </Button>
          ),
          <Link key="mua" to="/"><Button type={choThanhToan ? 'default' : 'primary'}>Tiếp tục mua sắm</Button></Link>,
        ]}
      />
      {choHoan && (
        <Alert
          style={{ marginBottom: 16 }}
          type="info"
          showIcon
          message="Khoản thanh toán của đơn này đang chờ hoàn tiền. Nhà thuốc sẽ xác nhận và hoàn lại cho bạn."
        />
      )}
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
