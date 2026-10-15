import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Descriptions, Result, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { laLoiApi } from '../../../api/loi'
import type { components } from '../../../api/schema'
import { NhanTrangThai } from '../../../components/NhanTrangThai'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { KHOA_QUERY_KHACH } from './khach'
import { NhanTaiKhoan } from './NhanTaiKhoan'
import { NutKhoaMoKhoaKhach } from './NutKhoaMoKhoaKhach'

type DonHang = components['schemas']['DonHangCuaKhach']

const KICH_THUOC_DON = 10
const ID_TOI_DA = 2_147_483_647 // khớp `IdInt` của backend: ngoài khoảng là 400 chứ không phải 404, nên chặn từ đầu
const GIOI_TINH: Record<string, string> = { nam: 'Nam', nu: 'Nữ', khac: 'Khác' }

function docId(gia: string | undefined): number | null {
  if (!gia || !/^[1-9]\d*$/.test(gia)) return null
  const so = Number(gia)
  return Number.isSafeInteger(so) && so <= ID_TOI_DA ? so : null
}

function KhongTimThay() {
  return (
    <Result
      status="404"
      title="Không tìm thấy khách hàng"
      subTitle="Khách không tồn tại hoặc đã xóa tài khoản."
      extra={
        <Link to=".." relative="path">
          <Button type="primary">Về danh sách khách hàng</Button>
        </Link>
      }
    />
  )
}

/**
 * Chi tiết khách hàng (AD02): thông tin liên hệ, trạng thái, khóa/mở khóa và lịch sử mua. KHÔNG có hồ sơ sức khỏe hay dị ứng:
 * Admin không được đọc (spec 03 mục 5.1), backend cũng không trả về.
 */
export default function TrangChiTietKhachHang() {
  const khachId = docId(useParams().id)
  const [tham, datTham] = useSearchParams()
  const trangDon = Math.max(1, Number(tham.get('trang')) || 1)

  const chiTiet = useQuery({
    queryKey: [...KHOA_QUERY_KHACH, 'chi-tiet', khachId],
    enabled: khachId !== null,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/khach-hang/{khach_id}', { params: { path: { khach_id: khachId! } } })
      if (error) throw error
      return data
    },
  })
  const donHang = useQuery({
    queryKey: [...KHOA_QUERY_KHACH, 'don-hang', khachId, trangDon],
    enabled: khachId !== null && chiTiet.isSuccess,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/khach-hang/{khach_id}/don-hang', {
        params: { path: { khach_id: khachId! }, query: { trang: trangDon, kich_thuoc: KICH_THUOC_DON } },
      })
      if (error) throw error
      return data
    },
  })

  if (khachId === null || (chiTiet.isError && laLoiApi(chiTiet.error) && chiTiet.error.ma_loi === 'KHONG_TIM_THAY')) return <KhongTimThay />
  if (chiTiet.isError) return <Alert type="error" showIcon title="Không tải được thông tin khách hàng" />
  const khach = chiTiet.data
  if (!khach) return null

  const cot: ColumnsType<DonHang> = [
    { title: 'Mã đơn', dataIndex: 'ma_don', render: (v: string) => <code>{v}</code> },
    { title: 'Ngày đặt', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
    { title: 'Kênh', dataIndex: 'kenh_ban', render: (v: string) => <NhanTrangThai loai="kenh_ban" giaTri={v} /> },
    { title: 'Trạng thái đơn', dataIndex: 'trang_thai', render: (v: string) => <NhanTrangThai loai="don_hang" giaTri={v} /> },
    { title: 'Thanh toán', dataIndex: 'trang_thai_tt', render: (v: string) => <NhanTrangThai loai="thanh_toan" giaTri={v} /> },
    { title: 'Tổng tiền', dataIndex: 'tong_tien', align: 'right', render: (v: string) => dinhDangTien(v) },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        <Link to=".." relative="path">
          ← Danh sách khách hàng
        </Link>
      </Space>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {khach.ho_ten}
        </Typography.Title>
        <NutKhoaMoKhoaKhach khach={khach} kieu="default" />
      </div>

      <Descriptions bordered size="small" column={{ xs: 1, md: 2 }} style={{ marginBottom: 12 }}>
        <Descriptions.Item label="Số điện thoại">{khach.so_dien_thoai}</Descriptions.Item>
        <Descriptions.Item label="Email">{khach.email ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="Giới tính">{khach.gioi_tinh ? (GIOI_TINH[khach.gioi_tinh] ?? khach.gioi_tinh) : '—'}</Descriptions.Item>
        <Descriptions.Item label="Trạng thái">
          <NhanTaiKhoan khach={khach} />
        </Descriptions.Item>
        <Descriptions.Item label="Ngày đăng ký">{dinhDangNgay(khach.created_at, 'ngayGio')}</Descriptions.Item>
        <Descriptions.Item label="Đồng ý chính sách lúc">{dinhDangNgay(khach.dong_y_chinh_sach_luc, 'ngayGio')}</Descriptions.Item>
        <Descriptions.Item label="Số đơn hàng">{khach.so_don_hang}</Descriptions.Item>
      </Descriptions>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
        title="Hồ sơ sức khỏe và dị ứng của khách không hiển thị với quản trị viên (Nghị định 13/2023/NĐ-CP)."
      />

      <Typography.Title level={4}>Lịch sử mua</Typography.Title>
      {donHang.isError && <Alert type="error" showIcon title="Không tải được lịch sử mua" style={{ marginBottom: 16 }} />}
      <Table<DonHang>
        rowKey="id"
        size="small"
        columns={cot}
        loading={donHang.isPending}
        dataSource={donHang.data?.du_lieu ?? []}
        pagination={{
          current: trangDon,
          pageSize: KICH_THUOC_DON,
          total: donHang.data?.tong ?? 0,
          showSizeChanger: false,
          onChange: (t) => {
            const moi = new URLSearchParams(tham)
            if (t > 1) moi.set('trang', String(t))
            else moi.delete('trang')
            datTham(moi, { replace: true })
          },
        }}
        locale={{ emptyText: 'Khách chưa có đơn hàng nào' }}
      />
    </div>
  )
}
