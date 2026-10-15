import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangChiTietKhachHang from './TrangChiTietKhachHang'

vi.setConfig({ testTimeout: 20_000 })

const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a) } }))

const CHI_TIET = {
  id: 7,
  ho_ten: 'Phạm Thu Hà',
  email: 'ha@example.com',
  so_dien_thoai: '0933444555',
  gioi_tinh: 'nu',
  trang_thai: 'hoat_dong',
  khoa_den: null,
  dong_y_chinh_sach_luc: '2026-09-01T02:31:00Z',
  created_at: '2026-09-01T02:30:00Z',
  updated_at: null,
  so_don_hang: 2,
}
const DON = [
  { id: 11, ma_don: 'DH000011', kenh_ban: 'online', trang_thai: 'da_giao', trang_thai_tt: 'da_thanh_toan', tong_tien: '125000.00', created_at: '2026-10-02T04:00:00Z' },
  { id: 10, ma_don: 'DH000010', kenh_ban: 'dien_thoai', trang_thai: 'cho_xac_nhan', trang_thai_tt: 'chua_thanh_toan', tong_tien: '99500.00', created_at: '2026-09-20T04:00:00Z' },
]
const ok = (data: unknown) => ({ data, response: { status: 200 } })
const trang = (du_lieu: unknown[], tong = du_lieu.length) => ok({ du_lieu, tong, trang: 1, kich_thuoc: 10 })

let chiTietHienTai: Record<string, unknown>
function dungGET(don: unknown = trang(DON)) {
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/khach-hang/{khach_id}') return ok(chiTietHienTai)
    if (duong === '/api/v1/noi-bo/khach-hang/{khach_id}/don-hang') return don
    throw new Error(`GET không mong đợi: ${duong}`)
  })
}

function dung(duong = '/khach-hang/7', quyen: 'day_du' | 'chi_xem' = 'day_du', goc = '') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'customer.manage': quyen } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <Routes>
              <Route path={`${goc}/khach-hang`} element={<div>DANH SÁCH KHÁCH</div>} />
              <Route path={`${goc}/khach-hang/:id`} element={<TrangChiTietKhachHang />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  chiTietHienTai = { ...CHI_TIET }
  dungGET()
})

describe('TrangChiTietKhachHang', () => {
  it('hiện thông tin liên hệ, giới tính, ngày giờ VN, số đơn và nhắc rằng hồ sơ sức khỏe không hiển thị với Admin', async () => {
    dung()
    expect(await screen.findByRole('heading', { name: 'Phạm Thu Hà' })).toBeInTheDocument()
    expect(screen.getByText('0933444555')).toBeInTheDocument()
    expect(screen.getByText('ha@example.com')).toBeInTheDocument()
    expect(screen.getByText('Nữ')).toBeInTheDocument()
    expect(screen.getByText('01/09/2026 09:30')).toBeInTheDocument() // đăng ký 02:30 UTC = 09:30 giờ Việt Nam
    expect(screen.getByText('01/09/2026 09:31')).toBeInTheDocument() // đồng ý chính sách
    expect(screen.getByText('Hoạt động')).toBeInTheDocument()
    expect(screen.getByText(/Hồ sơ sức khỏe và dị ứng của khách không hiển thị với quản trị viên/)).toBeInTheDocument()
    expect(GET).toHaveBeenCalledWith('/api/v1/noi-bo/khach-hang/{khach_id}', { params: { path: { khach_id: 7 } } })
  })

  it('không hiện trường sức khỏe hay hash mật khẩu dù máy chủ có lỡ trả về', async () => {
    chiTietHienTai = { ...CHI_TIET, benh_nen: 'Tiểu đường tuýp hai', mat_khau_hash: 'argon2id$xxx' }
    dung()
    await screen.findByRole('heading', { name: 'Phạm Thu Hà' })
    expect(document.body.textContent).not.toMatch(/Tiểu đường|argon2/)
  })

  it('lịch sử mua: nhãn tiếng Việt, tiền theo chuẩn VN, mới nhất trước đúng thứ tự máy chủ trả', async () => {
    dung()
    const hang1 = (await screen.findByText('DH000011')).closest('tr') as HTMLElement
    expect(within(hang1).getByText('Website')).toBeInTheDocument()
    expect(within(hang1).getByText('Đã giao')).toBeInTheDocument()
    expect(within(hang1).getByText('Đã thanh toán')).toBeInTheDocument()
    expect(within(hang1).getByText(/125\.000\s₫/)).toBeInTheDocument()
    const hang2 = screen.getByText('DH000010').closest('tr') as HTMLElement
    expect(within(hang2).getByText('Điện thoại')).toBeInTheDocument()
    expect(within(hang2).getByText('Chờ xác nhận')).toBeInTheDocument()
    expect(within(hang2).getByText(/99\.500\s₫/)).toBeInTheDocument()
    expect(GET).toHaveBeenCalledWith('/api/v1/noi-bo/khach-hang/{khach_id}/don-hang', { params: { path: { khach_id: 7 }, query: { trang: 1, kich_thuoc: 10 } } })
  })

  it('phân trang lịch sử mua gọi lại với số trang mới và giữ trong URL', async () => {
    dungGET(trang(DON, 25))
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('DH000011')
    await nguoi.click(screen.getByTitle('2'))
    await waitFor(() => expect(GET).toHaveBeenLastCalledWith('/api/v1/noi-bo/khach-hang/{khach_id}/don-hang', { params: { path: { khach_id: 7 }, query: { trang: 2, kich_thuoc: 10 } } }))
  })

  it('khách chưa có đơn thì báo rõ', async () => {
    dungGET(trang([]))
    dung()
    expect(await screen.findByText('Khách chưa có đơn hàng nào')).toBeInTheDocument()
  })

  it('khóa từ trang chi tiết: gửi POST kèm lý do, tải lại chi tiết và báo thành công', async () => {
    POST.mockImplementationOnce(async () => {
      chiTietHienTai = { ...CHI_TIET, trang_thai: 'bi_khoa' }
      return ok(chiTietHienTai)
    })
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: 'Khóa' }))
    const hop = await screen.findByRole('dialog')
    await nguoi.type(within(hop).getByRole('textbox', { name: /Lý do/ }), 'Gian lận')
    await nguoi.click(within(hop).getByRole('button', { name: 'Khóa tài khoản' }))
    await waitFor(() => expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/khach-hang/{khach_id}/khoa', { params: { path: { khach_id: 7 } }, body: { ly_do: 'Gian lận' } }))
    expect(await screen.findByText('Đã khóa Phạm Thu Hà')).toBeInTheDocument()
    expect(await screen.findByText('Bị khóa')).toBeInTheDocument() // chi tiết đã tải lại
    expect(await screen.findByRole('button', { name: 'Mở khóa' })).toBeInTheDocument()
  })

  it('mở khóa khách đang bị khóa', async () => {
    chiTietHienTai = { ...CHI_TIET, trang_thai: 'bi_khoa' }
    POST.mockImplementationOnce(async () => {
      chiTietHienTai = { ...CHI_TIET }
      return ok(chiTietHienTai)
    })
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: 'Mở khóa' }))
    await nguoi.click(within(await screen.findByRole('tooltip')).getByRole('button', { name: 'Mở khóa' }))
    await waitFor(() => expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/khach-hang/{khach_id}/mo-khoa', { params: { path: { khach_id: 7 } } }))
    expect(await screen.findByRole('button', { name: 'Khóa' })).toBeInTheDocument()
  })

  it('liên kết về danh sách giữ tiền tố của khu quản trị, cả ở trang chi tiết lẫn trang không tìm thấy', async () => {
    const { unmount } = dung('/quan-tri/khach-hang/7', 'day_du', '/quan-tri')
    expect(await screen.findByRole('link', { name: /Danh sách khách hàng/ })).toHaveAttribute('href', '/quan-tri/khach-hang')
    unmount()
    GET.mockImplementation(async () => ({ error: { ma_loi: 'KHONG_TIM_THAY', thong_diep: 'Không tìm thấy khách hàng', chi_tiet: null }, response: { status: 404 } }))
    dung('/quan-tri/khach-hang/7', 'day_du', '/quan-tri')
    expect(await screen.findByRole('link', { name: 'Về danh sách khách hàng' })).toHaveAttribute('href', '/quan-tri/khach-hang')
  })

  it('chỉ có quyền xem thì không có nút khóa', async () => {
    dung('/khach-hang/7', 'chi_xem')
    await screen.findByRole('heading', { name: 'Phạm Thu Hà' })
    expect(screen.queryByRole('button', { name: /Khóa/ })).not.toBeInTheDocument()
  })

  it('khách không tồn tại: báo không tìm thấy kèm đường về danh sách', async () => {
    GET.mockImplementation(async () => ({ error: { ma_loi: 'KHONG_TIM_THAY', thong_diep: 'Không tìm thấy khách hàng', chi_tiet: null }, response: { status: 404 } }))
    dung()
    expect(await screen.findByText('Không tìm thấy khách hàng')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Về danh sách khách hàng' })).toHaveAttribute('href', '/khach-hang')
  })

  it.each(['abc', '0', '-3', '2147483648', '1.5'])('id không hợp lệ "%s" thì không gọi máy chủ mà báo không tìm thấy', async (id) => {
    dung(`/khach-hang/${id}`)
    expect(await screen.findByText('Không tìm thấy khách hàng')).toBeInTheDocument()
    expect(GET).not.toHaveBeenCalled()
  })

  it('lỗi hệ thống khi tải chi tiết hiện thông báo lỗi chung, không giả làm không tìm thấy', async () => {
    GET.mockImplementation(async () => ({ error: { ma_loi: 'LOI_HE_THONG', thong_diep: 'Lỗi', chi_tiet: null }, response: { status: 500 } }))
    dung()
    expect(await screen.findByText('Không tải được thông tin khách hàng')).toBeInTheDocument()
    expect(screen.queryByText('Không tìm thấy khách hàng')).not.toBeInTheDocument()
  })
})
