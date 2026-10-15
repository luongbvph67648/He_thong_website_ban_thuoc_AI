import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../stores/phien'
import TrangTaiKhoanNoiBo from './TrangTaiKhoan'

const POST = vi.fn()
const PATCH = vi.fn()
vi.mock('../../api/client', () => ({
  api: { POST: (...tham_so: unknown[]) => POST(...tham_so), PATCH: (...tham_so: unknown[]) => PATCH(...tham_so) },
}))

const hoSoApi = (tuyChinh: Record<string, unknown> = {}) => ({
  id: 5,
  ma_nhan_vien: 'NV0005',
  ho_ten: 'Nguyễn Thị Lan',
  email: 'lan@example.com',
  so_dien_thoai: '0912345678',
  vai_tro: { ma: 'PHARMACIST', ten: 'Dược sĩ bán hàng' },
  phai_doi_mat_khau: false,
  quyen: { 'profile.self': 'day_du' },
  ...tuyChinh,
})
const ok = (data: unknown) => ({ data, response: { status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({
  error: { ma_loi, thong_diep, chi_tiet },
  response: { status },
})

function dangNhapSan(phaiDoi = false, vaiTro = 'PHARMACIST') {
  usePhien.getState().dangNhap({
    accessToken: 'tok-cu',
    loai: 'noi_bo',
    hoSo: { id: 5, hoTen: 'Nguyễn Thị Lan', vaiTro, maNhanVien: 'NV0005', email: 'lan@example.com', soDienThoai: '0912345678' },
    quyen: { 'profile.self': 'day_du' },
    phaiDoiMatKhau: phaiDoi,
  })
}

function dung() {
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <MemoryRouter initialEntries={['/nhan-vien/tai-khoan']}>
          <Routes>
            <Route path="/nhan-vien/tai-khoan" element={<TrangTaiKhoanNoiBo />} />
            <Route path="/nhan-vien/dang-nhap" element={<p>Trang đăng nhập nội bộ</p>} />
            <Route path="/nhan-vien" element={<p>Khu nhân viên</p>} />
            <Route path="/quan-tri" element={<p>Khu quản trị</p>} />
          </Routes>
        </MemoryRouter>
      </App>
    </ConfigProvider>,
  )
}

type Nguoi = ReturnType<typeof userEvent.setup>
const o = (nhan: RegExp | string) => screen.getByLabelText(nhan)

async function dienMatKhau(nguoi: Nguoi, { cu = 'Matkhaucu1', moi = 'Matkhaumoi2', xn }: { cu?: string; moi?: string; xn?: string } = {}) {
  await nguoi.type(o('Mật khẩu hiện tại'), cu)
  await nguoi.type(o('Mật khẩu mới'), moi)
  await nguoi.type(o('Nhập lại mật khẩu mới'), xn ?? moi)
}

describe('TrangTaiKhoanNoiBo', () => {
  beforeEach(() => {
    POST.mockReset()
    PATCH.mockReset()
    localStorage.clear()
    usePhien.getState().dangXuat()
  })

  it('chưa đăng nhập nội bộ thì chuyển tới trang đăng nhập; phiên khách cũng vậy', async () => {
    dung()
    expect(await screen.findByText('Trang đăng nhập nội bộ')).toBeInTheDocument()
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'khach', hoSo: { id: 1, hoTen: 'Khách' }, quyen: {} })
    dung()
    expect((await screen.findAllByText('Trang đăng nhập nội bộ')).length).toBeGreaterThan(0)
  })

  it('hiện hồ sơ: thông tin cố định chỉ đọc, họ tên và số điện thoại sửa được', async () => {
    dangNhapSan()
    dung()
    expect(screen.getByText('NV0005')).toBeInTheDocument()
    expect(screen.getByText('lan@example.com')).toBeInTheDocument()
    expect(screen.getByText('Dược sĩ bán hàng')).toBeInTheDocument()
    expect(o('Họ và tên')).toHaveValue('Nguyễn Thị Lan')
    expect(o(/Số điện thoại/)).toHaveValue('0912345678')
    expect(screen.getByRole('link', { name: /Quay lại/ })).toHaveAttribute('href', '/nhan-vien')
  })

  it('Admin quay lại khu quản trị', () => {
    dangNhapSan(false, 'ADMIN')
    dung()
    expect(screen.getByRole('link', { name: /Quay lại/ })).toHaveAttribute('href', '/quan-tri')
  })

  it('lưu hồ sơ: gửi đúng thân PATCH, cập nhật store và giữ nguyên token', async () => {
    dangNhapSan()
    PATCH.mockResolvedValueOnce(ok(hoSoApi({ ho_ten: 'Lan Mới', so_dien_thoai: null })))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.clear(o('Họ và tên'))
    await nguoi.type(o('Họ và tên'), '  Lan Mới ')
    await nguoi.clear(o(/Số điện thoại/))
    await nguoi.click(screen.getByRole('button', { name: 'Lưu hồ sơ' }))
    await waitFor(() => expect(usePhien.getState().hoSo?.hoTen).toBe('Lan Mới'))
    expect(PATCH).toHaveBeenCalledWith('/api/v1/noi-bo/toi', { body: { ho_ten: 'Lan Mới', so_dien_thoai: null } })
    expect(usePhien.getState().hoSo?.soDienThoai).toBeNull()
    expect(usePhien.getState().accessToken).toBe('tok-cu')
    expect(await screen.findByText('Đã lưu hồ sơ')).toBeInTheDocument()
  })

  it('số điện thoại sai hoặc họ tên trống thì báo ngay và không gọi API', async () => {
    dangNhapSan()
    const nguoi = userEvent.setup()
    dung()
    await nguoi.clear(o('Họ và tên'))
    await nguoi.clear(o(/Số điện thoại/))
    await nguoi.type(o(/Số điện thoại/), '0212345678')
    await nguoi.click(screen.getByRole('button', { name: 'Lưu hồ sơ' }))
    expect(await screen.findByText('Vui lòng nhập họ và tên')).toBeInTheDocument()
    expect(screen.getByText(/Số điện thoại không hợp lệ/)).toBeInTheDocument()
    expect(PATCH).not.toHaveBeenCalled()
  })

  it('lỗi validate của máy chủ gắn vào đúng ô', async () => {
    dangNhapSan()
    PATCH.mockResolvedValueOnce(loi(400, 'DU_LIEU_KHONG_HOP_LE', 'Dữ liệu không hợp lệ', [{ truong: 'so_dien_thoai', loi: 'Số điện thoại không hợp lệ' }]))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(screen.getByRole('button', { name: 'Lưu hồ sơ' }))
    expect(await screen.findByText('Số điện thoại không hợp lệ')).toBeInTheDocument()
  })

  it('đổi mật khẩu thành công: dùng token mới, các thiết bị khác bị đăng xuất, form được làm sạch', async () => {
    dangNhapSan()
    POST.mockResolvedValueOnce(ok({ access_token: 'tok-moi', token_type: 'bearer', het_han_giay: 900, nhan_vien: hoSoApi() }))
    const nguoi = userEvent.setup()
    dung()
    await dienMatKhau(nguoi)
    await nguoi.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
    expect(await screen.findByText('Đã đổi mật khẩu. Các thiết bị khác đã bị đăng xuất.')).toBeInTheDocument()
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/auth/doi-mat-khau', { body: { mat_khau_cu: 'Matkhaucu1', mat_khau_moi: 'Matkhaumoi2' } })
    expect(usePhien.getState().accessToken).toBe('tok-moi')
    expect(o('Mật khẩu hiện tại')).toHaveValue('')
    expect(JSON.stringify({ ...localStorage })).not.toContain('tok-moi')
  })

  it('mật khẩu yếu, trùng mật khẩu cũ hoặc nhập lại không khớp thì báo ngay và không gọi API', async () => {
    dangNhapSan()
    const nguoi = userEvent.setup()
    dung()
    await dienMatKhau(nguoi, { cu: 'Matkhaucu1', moi: 'chuchuchu', xn: 'khac' })
    await nguoi.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
    expect(await screen.findByText(/tối thiểu 8 ký tự, gồm cả chữ và số/)).toBeInTheDocument()
    expect(screen.getByText('Mật khẩu nhập lại không khớp')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()

    await nguoi.clear(o('Mật khẩu mới'))
    await nguoi.type(o('Mật khẩu mới'), 'Matkhaucu1')
    await nguoi.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
    expect(await screen.findByText('Mật khẩu mới phải khác mật khẩu hiện tại')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('mật khẩu hiện tại sai: báo ở đúng ô, không đổi phiên', async () => {
    dangNhapSan()
    POST.mockResolvedValueOnce(loi(422, 'MAT_KHAU_CU_SAI', 'Mật khẩu hiện tại không đúng'))
    const nguoi = userEvent.setup()
    dung()
    await dienMatKhau(nguoi)
    await nguoi.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
    expect(await screen.findByText('Mật khẩu hiện tại không đúng')).toBeInTheDocument()
    expect(usePhien.getState().accessToken).toBe('tok-cu')
  })

  it('bị khóa tạm do đoán mật khẩu cũ: nói rõ phải chờ bao lâu', async () => {
    dangNhapSan()
    POST.mockResolvedValueOnce(loi(403, 'TAI_KHOAN_BI_KHOA', 'Tài khoản bị khóa tạm do nhập sai nhiều lần', { thu_lai_sau_giay: 900 }))
    const nguoi = userEvent.setup()
    dung()
    await dienMatKhau(nguoi)
    await nguoi.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
    expect(await screen.findByText(/Hãy thử lại sau 15 phút/)).toBeInTheDocument()
  })

  describe('khi bị bắt đổi mật khẩu', () => {
    it('chỉ còn form đổi mật khẩu kèm giải thích; không có hồ sơ và nút quay lại', () => {
      dangNhapSan(true)
      dung()
      expect(screen.getByText('Bạn cần đổi mật khẩu trước khi tiếp tục')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Đổi mật khẩu' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Lưu hồ sơ' })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /Quay lại/ })).not.toBeInTheDocument()
    })

    it('đổi xong thì vào khu làm việc theo vai trò (Admin vào quản trị)', async () => {
      dangNhapSan(true, 'ADMIN')
      POST.mockResolvedValueOnce(ok({ access_token: 'tok-moi', token_type: 'bearer', het_han_giay: 900, nhan_vien: hoSoApi({ vai_tro: { ma: 'ADMIN', ten: 'Quản trị' } }) }))
      const nguoi = userEvent.setup()
      dung()
      await dienMatKhau(nguoi)
      await nguoi.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
      expect(await screen.findByText('Khu quản trị')).toBeInTheDocument()
      expect(usePhien.getState().phaiDoiMatKhau).toBe(false)
    })

    it('đổi xong, nhân viên thường vào khu nhân viên', async () => {
      dangNhapSan(true)
      POST.mockResolvedValueOnce(ok({ access_token: 'tok-moi', token_type: 'bearer', het_han_giay: 900, nhan_vien: hoSoApi() }))
      const nguoi = userEvent.setup()
      dung()
      await dienMatKhau(nguoi)
      await nguoi.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
      expect(await screen.findByText('Khu nhân viên')).toBeInTheDocument()
    })
  })
})
