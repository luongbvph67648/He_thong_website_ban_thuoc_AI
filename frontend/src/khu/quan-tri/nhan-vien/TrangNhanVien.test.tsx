import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangNhanVien from './TrangNhanVien'

// Bảng antd + hộp xác nhận dựng DOM lớn nên truy vấn theo role chậm; nới thời hạn mặc định 5 giây.
vi.setConfig({ testTimeout: 20_000 })

const GET = vi.fn()
const POST = vi.fn()
const PATCH = vi.fn()
const DELETE = vi.fn()
vi.mock('../../../api/client', () => ({
  api: {
    GET: (...a: unknown[]) => GET(...a),
    POST: (...a: unknown[]) => POST(...a),
    PATCH: (...a: unknown[]) => PATCH(...a),
    DELETE: (...a: unknown[]) => DELETE(...a),
  },
}))

const nv = (id: number, tuyChinh: Record<string, unknown> = {}) => ({
  id,
  ma_nhan_vien: `NV${String(id).padStart(4, '0')}`,
  ho_ten: `Nhân viên ${id}`,
  email: `nv${id}@example.com`,
  so_dien_thoai: null,
  vai_tro: { ma: 'WAREHOUSE', ten: 'Nhân viên kho' },
  trang_thai: 'hoat_dong',
  phai_doi_mat_khau: false,
  khoa_den: null,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: null,
  ...tuyChinh,
})
const VAI_TRO = [
  { ma: 'PHARMACIST', ten: 'Dược sĩ bán hàng', mo_ta: null, so_nhan_vien: 1, so_quyen: 20, chinh_sua_duoc: true },
  { ma: 'WAREHOUSE', ten: 'Nhân viên kho', mo_ta: null, so_nhan_vien: 1, so_quyen: 18, chinh_sua_duoc: true },
  { ma: 'ADMIN', ten: 'Quản trị', mo_ta: null, so_nhan_vien: 1, so_quyen: 20, chinh_sua_duoc: false },
]
const ok = (data: unknown) => ({ data, response: { status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({
  error: { ma_loi, thong_diep, chi_tiet },
  response: { status },
})

let danhSach = [nv(1, { ho_ten: 'Admin Gốc', vai_tro: { ma: 'ADMIN', ten: 'Quản trị' } }), nv(2), nv(3, { trang_thai: 'bi_khoa', ho_ten: 'Bị Khóa' })]

function ViTri() {
  const v = useLocation()
  return <span data-testid="vitri">{v.search}</span>
}

function dung(duong = '/quan-tri/nhan-vien') {
  usePhien.getState().dangNhap({
    accessToken: 't',
    loai: 'noi_bo',
    hoSo: { id: 1, hoTen: 'Admin Gốc', vaiTro: 'ADMIN' },
    quyen: { 'staff.manage': 'day_du', 'profile.self': 'day_du' },
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <TrangNhanVien />
            <ViTri />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

const dong = async (ten: string) => (await screen.findByText(ten)).closest('tr') as HTMLElement

beforeEach(() => {
  for (const m of [GET, POST, PATCH, DELETE]) m.mockReset()
  danhSach = [nv(1, { ho_ten: 'Admin Gốc', vai_tro: { ma: 'ADMIN', ten: 'Quản trị' } }), nv(2), nv(3, { trang_thai: 'bi_khoa', ho_ten: 'Bị Khóa' })]
  GET.mockImplementation(async (duong: string) =>
    duong.endsWith('/vai-tro') ? ok(VAI_TRO) : ok({ du_lieu: danhSach, tong: danhSach.length, trang: 1, kich_thuoc: 20 }),
  )
})

describe('TrangNhanVien', () => {
  it('liệt kê nhân viên với vai trò, trạng thái và các cờ', async () => {
    danhSach = [...danhSach, nv(4, { phai_doi_mat_khau: true, ho_ten: 'Mới Tạo' })]
    dung()
    const hang = await dong('Bị Khóa')
    expect(within(hang).getByText('Bị khóa')).toBeInTheDocument()
    expect(within(await dong('Mới Tạo')).getByText('Chờ đổi mật khẩu')).toBeInTheDocument()
    expect(within(await dong('Nhân viên 2')).getByText('Nhân viên kho')).toBeInTheDocument()
    expect(GET).toHaveBeenCalledWith('/api/v1/noi-bo/nhan-vien', { params: { query: { q: undefined, vai_tro: undefined, trang_thai: undefined, trang: 1, kich_thuoc: 20 } } })
  })

  it('tìm kiếm và lọc đẩy lên đường dẫn và gửi tham số tới API; về trang 1', async () => {
    const nguoi = userEvent.setup()
    dung('/quan-tri/nhan-vien?trang=3')
    await dong('Nhân viên 2')
    await nguoi.type(screen.getByPlaceholderText(/Tìm theo tên/), 'hoa{enter}')
    await waitFor(() => expect(screen.getByTestId('vitri')).toHaveTextContent('?q=hoa'))
    expect(screen.getByTestId('vitri')).not.toHaveTextContent('trang=')
    await waitFor(() => expect(GET).toHaveBeenLastCalledWith('/api/v1/noi-bo/nhan-vien', { params: { query: expect.objectContaining({ q: 'hoa', trang: 1 }) } }))

    await nguoi.click(screen.getByLabelText('Lọc theo trạng thái'))
    await nguoi.click(await screen.findByTitle('Bị khóa'))
    await waitFor(() => expect(screen.getByTestId('vitri')).toHaveTextContent('trang_thai=bi_khoa'))
  })

  it('dòng của chính mình không khóa, xóa, đặt lại mật khẩu được (nút bị tắt kèm giải thích)', async () => {
    dung()
    const toi = await dong('Admin Gốc')
    for (const ten of ['Khóa', 'Đặt lại mật khẩu', 'Xóa']) expect(within(toi).getByRole('button', { name: ten })).toBeDisabled()
    const nguoiKhac = await dong('Nhân viên 2')
    for (const ten of ['Khóa', 'Đặt lại mật khẩu', 'Xóa']) expect(within(nguoiKhac).getByRole('button', { name: ten })).toBeEnabled()
  })

  it('nhân viên đang bị khóa có nút Mở khóa thay cho Khóa', async () => {
    dung()
    const hang = await dong('Bị Khóa')
    expect(within(hang).getByRole('button', { name: 'Mở khóa' })).toBeInTheDocument()
    expect(within(hang).queryByRole('button', { name: 'Khóa' })).not.toBeInTheDocument()
  })

  it('tạo nhân viên: gửi đúng thân, hiện mật khẩu tạm MỘT LẦN kèm cảnh báo, đóng rồi không còn', async () => {
    POST.mockResolvedValueOnce(ok({ ...nv(9, { ho_ten: 'Trần Văn Mới' }), mat_khau_tam: 'Abc23456xyz9' }))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: /Thêm nhân viên/ }))
    await nguoi.type(screen.getByLabelText('Họ và tên'), '  Trần Văn Mới ')
    await nguoi.type(screen.getByLabelText('Email đăng nhập'), 'moi@example.com')
    await nguoi.type(screen.getByLabelText(/Số điện thoại/), '0912345678')
    await nguoi.click(screen.getByRole('combobox', { name: /Vai trò/ }))
    await nguoi.click(await screen.findByTitle('Nhân viên kho'))
    await nguoi.click(screen.getByRole('button', { name: 'Lưu' }))

    expect(await screen.findByText('Mật khẩu tạm chỉ hiện một lần')).toBeInTheDocument()
    expect(screen.getByLabelText('Mật khẩu tạm')).toHaveTextContent('Abc23456xyz9')
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/nhan-vien', {
      body: { ho_ten: 'Trần Văn Mới', email: 'moi@example.com', so_dien_thoai: '0912345678', vai_tro: 'WAREHOUSE' },
    })
    await nguoi.click(screen.getByRole('button', { name: /Đã ghi lại, đóng/ }))
    // Hộp thoại gỡ khỏi DOM ngay khi đóng: mật khẩu tạm không nằm lại trong trang.
    await waitFor(() => expect(document.body.textContent).not.toContain('Abc23456xyz9'))
  })

  it('tạo: để trống hoặc sai định dạng thì báo ngay và không gọi API', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: /Thêm nhân viên/ }))
    await nguoi.type(screen.getByLabelText('Email đăng nhập'), 'khong-phai-email')
    await nguoi.type(screen.getByLabelText(/Số điện thoại/), '0212345678')
    await nguoi.click(screen.getByRole('button', { name: 'Lưu' }))
    expect(await screen.findByText('Vui lòng nhập họ và tên')).toBeInTheDocument()
    expect(screen.getByText('Email không hợp lệ')).toBeInTheDocument()
    expect(screen.getByText(/Số điện thoại không hợp lệ/)).toBeInTheDocument()
    expect(screen.getByText('Vui lòng chọn vai trò')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('tạo trùng email: lỗi gắn vào ô email, form vẫn mở', async () => {
    POST.mockResolvedValueOnce(loi(409, 'TRUNG_DU_LIEU', 'Email này đã được dùng cho một tài khoản nhân viên', { truong: 'email' }))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: /Thêm nhân viên/ }))
    await nguoi.type(screen.getByLabelText('Họ và tên'), 'Ai Đó')
    await nguoi.type(screen.getByLabelText('Email đăng nhập'), 'trung@example.com')
    await nguoi.click(screen.getByRole('combobox', { name: /Vai trò/ }))
    await nguoi.click(await screen.findByTitle('Nhân viên kho'))
    await nguoi.click(screen.getByRole('button', { name: 'Lưu' }))
    expect(await screen.findByText('Email này đã được dùng cho một tài khoản nhân viên')).toBeInTheDocument()
    expect(screen.getByLabelText('Email đăng nhập')).toBeInTheDocument()
    expect(screen.queryByLabelText('Mật khẩu tạm')).not.toBeInTheDocument()
  })

  it('sửa nhân viên: điền sẵn dữ liệu, gửi PATCH; vai trò của chính mình bị tắt', async () => {
    PATCH.mockResolvedValueOnce(ok(nv(2, { ho_ten: 'Tên Mới' })))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Nhân viên 2')).getByRole('button', { name: 'Sửa' }))
    const ten = screen.getByLabelText('Họ và tên')
    expect(ten).toHaveValue('Nhân viên 2')
    await nguoi.clear(ten)
    await nguoi.type(ten, 'Tên Mới')
    await nguoi.click(screen.getByRole('button', { name: 'Lưu' }))
    await waitFor(() => expect(PATCH).toHaveBeenCalledWith('/api/v1/noi-bo/nhan-vien/{nhan_vien_id}', {
      params: { path: { nhan_vien_id: 2 } },
      body: { ho_ten: 'Tên Mới', email: 'nv2@example.com', so_dien_thoai: null, vai_tro: 'WAREHOUSE' },
    }))
    expect(PATCH).toHaveBeenCalledTimes(1)
  })

  it('sửa chính mình: ô vai trò bị tắt và có giải thích', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Admin Gốc')).getByRole('button', { name: 'Sửa' }))
    expect(screen.getByRole('combobox', { name: /Vai trò/ })).toBeDisabled()
    expect(screen.getByText('Bạn không thể tự đổi vai trò của mình.')).toBeInTheDocument()
  })

  it('khóa: hỏi xác nhận (chưa gọi API), đồng ý thì gọi API khóa rồi tải lại danh sách', async () => {
    POST.mockResolvedValueOnce(ok(nv(2, { trang_thai: 'bi_khoa' })))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Nhân viên 2')).getByRole('button', { name: 'Khóa' }))
    const hop = await screen.findByRole('tooltip')
    expect(within(hop).getByText(/đăng xuất khỏi mọi thiết bị/)).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
    const soLanTaiTruoc = GET.mock.calls.filter(([d]) => String(d).endsWith('/nhan-vien')).length
    await nguoi.click(within(hop).getByRole('button', { name: 'Khóa' }))
    await waitFor(() =>
      expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/nhan-vien/{nhan_vien_id}/khoa', { params: { path: { nhan_vien_id: 2 } } }),
    )
    await waitFor(() => expect(GET.mock.calls.filter(([d]) => String(d).endsWith('/nhan-vien')).length).toBeGreaterThan(soLanTaiTruoc))
  })

  it('hủy ở hộp xác nhận thì không gọi API', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Nhân viên 2')).getByRole('button', { name: 'Xóa' }))
    await nguoi.click(within(await screen.findByRole('tooltip')).getByRole('button', { name: 'Hủy' }))
    expect(DELETE).not.toHaveBeenCalled()
  })

  it('đặt lại mật khẩu: hiện mật khẩu tạm mới một lần', async () => {
    POST.mockResolvedValueOnce(ok({ ...nv(2), mat_khau_tam: 'Moi45678abcd', phai_doi_mat_khau: true }))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Nhân viên 2')).getByRole('button', { name: 'Đặt lại mật khẩu' }))
    await nguoi.click(within(await screen.findByRole('tooltip')).getByRole('button', { name: 'Đặt lại' }))
    expect(await screen.findByLabelText('Mật khẩu tạm')).toHaveTextContent('Moi45678abcd')
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/nhan-vien/{nhan_vien_id}/dat-lai-mat-khau', { params: { path: { nhan_vien_id: 2 } } })
  })

  it('xóa mềm: hỏi xác nhận, gọi DELETE, báo thành công và tải lại danh sách (204 không có thân)', async () => {
    // Đúng dạng openapi-fetch trả cho 204: data undefined, response.ok true. Từng báo nhầm "không kết nối được máy chủ".
    DELETE.mockResolvedValueOnce({ data: undefined, response: new Response(null, { status: 204 }) })
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Nhân viên 2')).getByRole('button', { name: 'Xóa' }))
    const soLanTaiDanhSach = () => GET.mock.calls.filter(([duong]) => duong === '/api/v1/noi-bo/nhan-vien').length
    const truoc = soLanTaiDanhSach()
    await nguoi.click(within(await screen.findByRole('tooltip')).getByRole('button', { name: 'Xóa' }))
    await waitFor(() =>
      expect(DELETE).toHaveBeenCalledWith('/api/v1/noi-bo/nhan-vien/{nhan_vien_id}', { params: { path: { nhan_vien_id: 2 } } }),
    )
    expect(await screen.findByText('Đã xóa Nhân viên 2')).toBeInTheDocument()
    expect(screen.queryByText(/Không kết nối được máy chủ/)).not.toBeInTheDocument()
    await waitFor(() => expect(soLanTaiDanhSach()).toBeGreaterThan(truoc))
  })

  it('thao tác bị máy chủ từ chối (Admin cuối cùng) thì báo thông điệp của máy chủ', async () => {
    POST.mockResolvedValueOnce(loi(409, 'PHAI_CON_ADMIN', 'Hệ thống phải luôn còn ít nhất một Admin đang hoạt động'))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await dong('Nhân viên 2')).getByRole('button', { name: 'Khóa' }))
    await nguoi.click(within(await screen.findByRole('tooltip')).getByRole('button', { name: 'Khóa' }))
    expect(await screen.findByText('Hệ thống phải luôn còn ít nhất một Admin đang hoạt động')).toBeInTheDocument()
  })

  it('danh sách lỗi thì báo thay vì để trống im lặng', async () => {
    GET.mockImplementation(async (duong: string) => (duong.endsWith('/vai-tro') ? ok(VAI_TRO) : { error: { ma_loi: 'LOI_HE_THONG', thong_diep: 'x', chi_tiet: null } }))
    dung()
    expect(await screen.findByText('Không tải được danh sách nhân viên')).toBeInTheDocument()
  })

  it('quyền chỉ xem thì không có nút thao tác', async () => {
    dung()
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'X', vaiTro: 'ADMIN' }, quyen: { 'staff.manage': 'chi_xem' } })
    await waitFor(() => expect(screen.queryByRole('button', { name: /Thêm nhân viên/ })).not.toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Sửa' })).not.toBeInTheDocument()
  })
})
