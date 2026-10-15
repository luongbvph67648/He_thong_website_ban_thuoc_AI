import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangKhachHang from './TrangKhachHang'

vi.setConfig({ testTimeout: 20_000 })

const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a) } }))

const KHACH = [
  { id: 1, ho_ten: 'Nguyễn Văn An', email: 'an@example.com', so_dien_thoai: '0901234567', trang_thai: 'hoat_dong', khoa_den: null, created_at: '2026-10-01T03:00:00Z' },
  { id: 2, ho_ten: 'Trần Thị Bình', email: null, so_dien_thoai: '0902345678', trang_thai: 'bi_khoa', khoa_den: null, created_at: '2026-09-15T20:00:00Z' },
  { id: 3, ho_ten: 'Lê Cường', email: 'cuong@example.com', so_dien_thoai: '0903456789', trang_thai: 'hoat_dong', khoa_den: '2099-01-01T00:00:00Z', created_at: '2026-08-01T00:00:00Z' },
]
const trang = (du_lieu: unknown[], tong = du_lieu.length) => ({ data: { du_lieu, tong, trang: 1, kich_thuoc: 20 }, response: { status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string) => ({ error: { ma_loi, thong_diep, chi_tiet: null }, response: { status } })

function dung(duong = '/khach-hang', quyen: 'day_du' | 'chi_xem' = 'day_du', goc = '') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'customer.manage': quyen } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <Routes>
              <Route path={`${goc}/khach-hang`} element={<TrangKhachHang />} />
              <Route path={`${goc}/khach-hang/:id`} element={<div>TRANG CHI TIẾT</div>} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

const thamSoGanNhat = () => GET.mock.calls.at(-1)?.[1]?.params?.query
const dong = async (ten: string) => (await screen.findByText(ten)).closest('tr') as HTMLElement

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockResolvedValue(trang(KHACH))
})

describe('TrangKhachHang', () => {
  it('liệt kê khách: tên là liên kết tới chi tiết, ngày giờ Việt Nam, thiếu email hiện —, nhãn trạng thái', async () => {
    dung()
    const hang = await dong('Nguyễn Văn An')
    expect(within(hang).getByRole('link', { name: 'Nguyễn Văn An' })).toHaveAttribute('href', '/khach-hang/1')
    expect(within(hang).getByText('0901234567')).toBeInTheDocument()
    expect(within(hang).getByText('01/10/2026')).toBeInTheDocument()
    expect(within(hang).getByText('Hoạt động')).toBeInTheDocument()
    const hangBinh = await dong('Trần Thị Bình')
    expect(within(hangBinh).getByText('—')).toBeInTheDocument() // không có email
    expect(within(hangBinh).getByText('16/09/2026')).toBeInTheDocument() // 20:00 UTC đã sang ngày hôm sau theo giờ VN
    expect(within(hangBinh).getByText('Bị khóa')).toBeInTheDocument()
    expect(within(await dong('Lê Cường')).getByText(/Khóa tạm đến/)).toBeInTheDocument()
    expect(thamSoGanNhat()).toEqual({ q: undefined, trang_thai: undefined, sap_xep: undefined, trang: 1, kich_thuoc: 20 })
  })

  it('liên kết giữ tiền tố của khu quản trị (/quan-tri/khach-hang/1), không bật ra ngoài khu', async () => {
    dung('/quan-tri/khach-hang?q=an', 'day_du', '/quan-tri')
    const hang = await dong('Nguyễn Văn An')
    expect(within(hang).getByRole('link', { name: 'Nguyễn Văn An' })).toHaveAttribute('href', '/quan-tri/khach-hang/1')
  })

  it('không hiện bất kỳ trường sức khỏe hay mật khẩu nào dù máy chủ có lỡ trả về', async () => {
    GET.mockResolvedValue(trang([{ ...KHACH[0], benh_nen: 'Tiểu đường tuýp hai', mat_khau_hash: 'argon2id$xxx' }]))
    dung()
    await screen.findByText('Nguyễn Văn An')
    expect(document.body.textContent).not.toMatch(/Tiểu đường|argon2/)
  })

  it('tìm kiếm và lọc đưa vào URL; mở trang từ URL thì gọi API đúng các tham số đó', async () => {
    const nguoi = userEvent.setup()
    dung('/khach-hang?q=an&trang_thai=bi_khoa&sap_xep=-ho_ten&trang=2')
    await screen.findByText('Nguyễn Văn An')
    expect(thamSoGanNhat()).toEqual({ q: 'an', trang_thai: 'bi_khoa', sap_xep: '-ho_ten', trang: 2, kich_thuoc: 20 })
    const o = screen.getByPlaceholderText(/Tìm theo tên/)
    expect(o).toHaveValue('an')
    await nguoi.clear(o)
    await nguoi.type(o, 'trần{Enter}')
    await waitFor(() => expect(thamSoGanNhat()).toEqual({ q: 'trần', trang_thai: 'bi_khoa', sap_xep: '-ho_ten', trang: 1, kich_thuoc: 20 })) // về trang 1
  })

  it('bấm nút chuyển trang: gọi API với trang mới, giữ nguyên tìm kiếm và sắp xếp, URL có trang', async () => {
    // Lỗi từng có: antd gọi cả `pagination.onChange` lẫn `Table.onChange` cho một lần bấm trang, và xử lý sắp xếp ở
    // `Table.onChange` xóa mất `trang` vừa đặt, nên không bao giờ sang được trang 2.
    GET.mockResolvedValue(trang(KHACH, 45))
    const nguoi = userEvent.setup()
    dung('/khach-hang?q=an&sap_xep=-ho_ten')
    await screen.findByText('Nguyễn Văn An')
    await nguoi.click(screen.getByTitle('2'))
    await waitFor(() => expect(thamSoGanNhat()).toEqual({ q: 'an', trang_thai: undefined, sap_xep: '-ho_ten', trang: 2, kich_thuoc: 20 }))
    await nguoi.click(screen.getByTitle('3'))
    await waitFor(() => expect(thamSoGanNhat().trang).toBe(3))
    await nguoi.click(screen.getByTitle('1'))
    await waitFor(() => expect(thamSoGanNhat().trang).toBe(1))
    expect(thamSoGanNhat().sap_xep).toBe('-ho_ten') // chuyển trang không làm mất sắp xếp
  })

  it('đổi sắp xếp khi đang ở trang 2 thì về trang 1', async () => {
    GET.mockResolvedValue(trang(KHACH, 45))
    const nguoi = userEvent.setup()
    dung('/khach-hang?trang=2')
    await screen.findByText('Nguyễn Văn An')
    await nguoi.click(screen.getByText('Họ và tên'))
    await waitFor(() => expect(thamSoGanNhat()).toMatchObject({ sap_xep: 'ho_ten', trang: 1 }))
  })

  it('bấm tiêu đề cột để sắp xếp: tăng, giảm rồi về mặc định', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Nguyễn Văn An')
    const tieuDe = screen.getByText('Họ và tên')
    await nguoi.click(tieuDe)
    await waitFor(() => expect(thamSoGanNhat().sap_xep).toBe('ho_ten'))
    await nguoi.click(tieuDe)
    await waitFor(() => expect(thamSoGanNhat().sap_xep).toBe('-ho_ten'))
    await nguoi.click(tieuDe)
    await waitFor(() => expect(thamSoGanNhat().sap_xep).toBeUndefined())
  })

  it('tham số sắp xếp lạ trên URL bị bỏ qua, không gửi lên máy chủ', async () => {
    dung('/khach-hang?sap_xep=mat_khau_hash&trang_thai=tuy_y')
    await screen.findByText('Nguyễn Văn An')
    expect(thamSoGanNhat().sap_xep).toBeUndefined()
    expect(thamSoGanNhat().trang_thai).toBeUndefined()
  })

  it('khóa: hộp thoại xác nhận có ô lý do (không bắt buộc), gửi POST đúng khách rồi tải lại danh sách', async () => {
    POST.mockResolvedValueOnce({ data: { ...KHACH[0], trang_thai: 'bi_khoa', so_don_hang: 0, gioi_tinh: null, dong_y_chinh_sach_luc: '2026-01-01T00:00:00Z', updated_at: null }, response: { status: 200 } })
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Nguyễn Văn An')).getByRole('button', { name: 'Khóa' }))
    const hop = await screen.findByRole('dialog')
    expect(within(hop).getByText(/đăng xuất khỏi mọi thiết bị/)).toBeInTheDocument()
    expect(within(hop).getByText(/Không nhập số điện thoại hay thông tin sức khỏe/)).toBeInTheDocument() // lý do không được kiểm tra nội dung
    expect(POST).not.toHaveBeenCalled()
    await nguoi.type(within(hop).getByRole('textbox', { name: /Lý do/ }), '  Hủy đơn liên tục  ')
    const truoc = GET.mock.calls.length
    await nguoi.click(within(hop).getByRole('button', { name: 'Khóa tài khoản' }))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/khach-hang/{khach_id}/khoa', { params: { path: { khach_id: 1 } }, body: { ly_do: 'Hủy đơn liên tục' } })
    expect(await screen.findByText('Đã khóa Nguyễn Văn An')).toBeInTheDocument()
    await waitFor(() => expect(GET.mock.calls.length).toBeGreaterThan(truoc))
  })

  it('khóa không điền lý do thì gửi ly_do null', async () => {
    POST.mockResolvedValueOnce({ data: { ...KHACH[0] }, response: { status: 200 } })
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Nguyễn Văn An')).getByRole('button', { name: 'Khóa' }))
    await nguoi.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Khóa tài khoản' }))
    await waitFor(() => expect(POST.mock.calls[0][1].body).toEqual({ ly_do: null }))
  })

  it('mở khóa cho khách bị khóa và cả khách đang bị khóa tạm; khách hoạt động bình thường thì chỉ có nút Khóa', async () => {
    POST.mockResolvedValue({ data: { ...KHACH[1] }, response: { status: 200 } })
    const nguoi = userEvent.setup()
    dung()
    expect(within(await dong('Nguyễn Văn An')).queryByRole('button', { name: 'Mở khóa' })).not.toBeInTheDocument()
    expect(within(await dong('Lê Cường')).getByRole('button', { name: 'Mở khóa' })).toBeInTheDocument() // khóa tạm
    await nguoi.click(within(await dong('Trần Thị Bình')).getByRole('button', { name: 'Mở khóa' }))
    await nguoi.click(within(await screen.findByRole('tooltip')).getByRole('button', { name: 'Mở khóa' }))
    await waitFor(() => expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/khach-hang/{khach_id}/mo-khoa', { params: { path: { khach_id: 2 } } }))
    expect(await screen.findByText('Đã mở khóa Trần Thị Bình')).toBeInTheDocument()
  })

  it('máy chủ từ chối thì báo thông điệp của máy chủ và không báo thành công', async () => {
    POST.mockResolvedValueOnce(loi(404, 'KHONG_TIM_THAY', 'Không tìm thấy khách hàng'))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Nguyễn Văn An')).getByRole('button', { name: 'Khóa' }))
    await nguoi.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Khóa tài khoản' }))
    expect(await screen.findByText('Không tìm thấy khách hàng')).toBeInTheDocument()
    expect(screen.queryByText(/Đã khóa/)).not.toBeInTheDocument()
  })

  it('chỉ có quyền xem thì không có nút khóa, mở khóa', async () => {
    dung('/khach-hang', 'chi_xem')
    await screen.findByText('Nguyễn Văn An')
    expect(screen.queryByRole('button', { name: /Khóa/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mở khóa' })).not.toBeInTheDocument()
  })

  it('danh sách rỗng và lỗi tải', async () => {
    GET.mockResolvedValueOnce(trang([]))
    const { unmount } = dung()
    expect(await screen.findByText('Không có khách hàng phù hợp')).toBeInTheDocument()
    unmount()
    GET.mockResolvedValue({ error: { ma_loi: 'LOI_HE_THONG', thong_diep: 'x', chi_tiet: null }, response: { status: 500 } })
    dung()
    expect(await screen.findByText('Không tải được danh sách khách hàng')).toBeInTheDocument()
  })
})
