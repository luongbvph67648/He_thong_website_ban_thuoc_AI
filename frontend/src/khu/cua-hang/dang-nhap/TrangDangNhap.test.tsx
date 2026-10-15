import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangDangNhap from './TrangDangNhap'

const POST = vi.fn()
vi.mock('../../../api/client', () => ({ api: { POST: (...tham_so: unknown[]) => POST(...tham_so) } }))

const ok = (data: unknown) => ({ data, response: { status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({
  error: { ma_loi, thong_diep, chi_tiet },
  response: { status },
})
const DANG_NHAP_OK = ok({
  access_token: 'tok-1',
  token_type: 'bearer',
  het_han_giay: 900,
  khach_hang: { id: 7, ho_ten: 'Nguyễn Thị Mai', so_dien_thoai: '0912345678', email: null },
})

function dung(duong = '/dang-nhap') {
  return render(
    <ConfigProvider locale={viVN}>
      <MemoryRouter initialEntries={[duong]}>
        <Routes>
          <Route path="/dang-nhap" element={<TrangDangNhap />} />
          <Route path="/" element={<p>Trang chủ</p>} />
          <Route path="/gio-hang" element={<p>Giỏ hàng của bạn</p>} />
          <Route path="/quen-mat-khau" element={<p>Trang quên mật khẩu</p>} />
          <Route path="/dang-ky" element={<p>Trang đăng ký</p>} />
        </Routes>
      </MemoryRouter>
    </ConfigProvider>,
  )
}

async function dangNhap(nguoi: ReturnType<typeof userEvent.setup>, ten = '0912345678', mk = 'Matkhau123') {
  await nguoi.type(screen.getByLabelText(/Số điện thoại hoặc email/), ten)
  await nguoi.type(screen.getByLabelText(/^Mật khẩu/), mk)
  await nguoi.click(screen.getByRole('button', { name: /^Đăng nhập$/ }))
}

describe('TrangDangNhap', () => {
  beforeEach(() => {
    POST.mockReset()
    localStorage.clear()
    usePhien.getState().dangXuat()
  })

  it('hiện form và liên kết quên mật khẩu, đăng ký', () => {
    dung()
    expect(screen.getByRole('heading', { name: 'Đăng nhập' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Quên mật khẩu?' })).toHaveAttribute('href', '/quen-mat-khau')
    expect(screen.getByRole('link', { name: 'Đăng ký' })).toHaveAttribute('href', '/dang-ky')
  })

  it('để trống thì báo lỗi ngay và không gọi API', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(screen.getByRole('button', { name: /^Đăng nhập$/ }))
    expect(await screen.findByText('Vui lòng nhập số điện thoại hoặc email')).toBeInTheDocument()
    expect(screen.getByText('Vui lòng nhập mật khẩu')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('đăng nhập thành công: gửi thông tin đã cắt khoảng trắng, lưu phiên vào store và về trang chủ', async () => {
    POST.mockResolvedValueOnce(DANG_NHAP_OK)
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi, '  0912345678  ')
    expect(await screen.findByText('Trang chủ')).toBeInTheDocument()
    expect(POST).toHaveBeenCalledWith('/api/v1/auth/dang-nhap', { body: { ten_dang_nhap: '0912345678', mat_khau: 'Matkhau123' } })
    const p = usePhien.getState()
    expect([p.loai, p.accessToken, p.hoSo]).toEqual(['khach', 'tok-1', { id: 7, hoTen: 'Nguyễn Thị Mai' }])
    expect(localStorage.getItem('phien_goi_y')).toBe('khach')
    expect(JSON.stringify({ ...localStorage })).not.toContain('tok-1')
  })

  it('quay lại trang trong ?tiep= sau khi đăng nhập', async () => {
    POST.mockResolvedValueOnce(DANG_NHAP_OK)
    const nguoi = userEvent.setup()
    dung('/dang-nhap?tiep=/gio-hang')
    await dangNhap(nguoi)
    expect(await screen.findByText('Giỏ hàng của bạn')).toBeInTheDocument()
  })

  it.each(['https://trang-lua-dao.example', '//trang-lua-dao.example', '/\\trang-lua-dao.example'])(
    '?tiep=%s không phải đường dẫn nội bộ nên về trang chủ',
    async (tiep) => {
      POST.mockResolvedValueOnce(DANG_NHAP_OK)
      const nguoi = userEvent.setup()
      dung(`/dang-nhap?tiep=${encodeURIComponent(tiep)}`)
      await dangNhap(nguoi)
      expect(await screen.findByText('Trang chủ')).toBeInTheDocument()
    },
  )

  it('sai thông tin: hiện thông điệp của máy chủ, xóa ô mật khẩu, không đăng nhập', async () => {
    POST.mockResolvedValueOnce(loi(401, 'SAI_THONG_TIN_DANG_NHAP', 'Số điện thoại/email hoặc mật khẩu không đúng'))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi)
    expect(await screen.findByText('Số điện thoại/email hoặc mật khẩu không đúng')).toBeInTheDocument()
    expect(screen.getByLabelText(/^Mật khẩu/)).toHaveValue('')
    expect(screen.getByLabelText(/Số điện thoại hoặc email/)).toHaveValue('0912345678')
    expect(usePhien.getState().loai).toBeNull()
  })

  it('khóa tạm: nói rõ phải chờ bao nhiêu phút', async () => {
    POST.mockResolvedValueOnce(loi(403, 'TAI_KHOAN_BI_KHOA', 'Tài khoản bị khóa tạm do nhập sai nhiều lần', { thu_lai_sau_giay: 900 }))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi)
    expect(await screen.findByText(/Hãy thử lại sau 15 phút/)).toBeInTheDocument()
  })

  it('tài khoản bị Admin khóa: hiện thông điệp, không hứa hẹn thử lại', async () => {
    POST.mockResolvedValueOnce(loi(403, 'TAI_KHOAN_BI_KHOA', 'Tài khoản đã bị khóa, vui lòng liên hệ nhà thuốc'))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi)
    expect(await screen.findByText('Tài khoản đã bị khóa, vui lòng liên hệ nhà thuốc')).toBeInTheDocument()
    expect(screen.queryByText(/thử lại sau/)).not.toBeInTheDocument()
  })

  it('quá giới hạn tần suất', async () => {
    POST.mockResolvedValueOnce(loi(429, 'QUA_GIOI_HAN', 'Bạn thử đăng nhập quá nhiều lần, vui lòng thử lại sau', { thu_lai_sau_giay: 120 }))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi)
    expect(await screen.findByText(/thử lại sau\. Hãy thử lại sau 2 phút/)).toBeInTheDocument()
  })

  it('mất mạng: báo không kết nối được thay vì treo', async () => {
    POST.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi)
    expect(await screen.findByText(/Không kết nối được máy chủ/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Đăng nhập$/ })).toBeEnabled()
  })

  it('bấm đăng nhập hai lần liên tiếp chỉ gửi một request', async () => {
    let xong: (v: unknown) => void = () => {}
    POST.mockReturnValueOnce(new Promise((r) => (xong = r)))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.type(screen.getByLabelText(/Số điện thoại hoặc email/), '0912345678')
    await nguoi.type(screen.getByLabelText(/^Mật khẩu/), 'Matkhau123')
    const nut = screen.getByRole('button', { name: /^Đăng nhập$/ })
    await nguoi.click(nut)
    await nguoi.click(nut)
    expect(POST).toHaveBeenCalledTimes(1)
    xong(DANG_NHAP_OK)
    await waitFor(() => expect(usePhien.getState().loai).toBe('khach'))
  })

  it('khách đã đăng nhập vào trang này thì được chuyển đi luôn, không thấy form', async () => {
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'khach', hoSo: { id: 1, hoTen: 'A' }, quyen: {} })
    dung('/dang-nhap?tiep=/gio-hang')
    expect(await screen.findByText('Giỏ hàng của bạn')).toBeInTheDocument()
    expect(screen.queryByLabelText(/^Mật khẩu/)).not.toBeInTheDocument()
  })
})
