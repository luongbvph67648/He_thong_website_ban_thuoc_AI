import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../stores/phien'
import TrangDangNhapNoiBo from './TrangDangNhap'

const POST = vi.fn()
vi.mock('../../api/client', () => ({ api: { POST: (...tham_so: unknown[]) => POST(...tham_so) } }))

const nhanVien = (vaiTro: string, phaiDoi = false) => ({
  id: 5,
  ma_nhan_vien: 'NV0005',
  ho_ten: 'Nguyễn Thị Lan',
  email: 'lan@example.com',
  so_dien_thoai: null,
  vai_tro: { ma: vaiTro, ten: vaiTro },
  phai_doi_mat_khau: phaiDoi,
  quyen: { 'profile.self': 'day_du', 'order.view': 'day_du' },
})
const ok = (nv: ReturnType<typeof nhanVien>) => ({
  data: { access_token: 'tok-nv', token_type: 'bearer', het_han_giay: 900, nhan_vien: nv },
  response: { status: 200 },
})
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({
  error: { ma_loi, thong_diep, chi_tiet },
  response: { status },
})

function dung(state?: unknown) {
  return render(
    <ConfigProvider locale={viVN}>
      <MemoryRouter initialEntries={[{ pathname: '/nhan-vien/dang-nhap', state }]}>
        <Routes>
          <Route path="/nhan-vien/dang-nhap" element={<TrangDangNhapNoiBo />} />
          <Route path="/nhan-vien" element={<p>Khu nhân viên</p>} />
          <Route path="/nhan-vien/don-hang" element={<p>Trang đơn hàng</p>} />
          <Route path="/nhan-vien/tai-khoan" element={<p>Trang tài khoản</p>} />
          <Route path="/quan-tri" element={<p>Khu quản trị</p>} />
          <Route path="/" element={<p>Trang chủ cửa hàng</p>} />
        </Routes>
      </MemoryRouter>
    </ConfigProvider>,
  )
}

async function dangNhap(nguoi: ReturnType<typeof userEvent.setup>, email = 'lan@example.com', mk = 'Matkhau123') {
  await nguoi.type(screen.getByLabelText('Email'), email)
  await nguoi.type(screen.getByLabelText('Mật khẩu'), mk)
  await nguoi.click(screen.getByRole('button', { name: /^Đăng nhập$/ }))
}

describe('TrangDangNhapNoiBo', () => {
  beforeEach(() => {
    POST.mockReset()
    localStorage.clear()
    usePhien.getState().dangXuat()
    usePhien.setState({ daKhoiPhuc: true })
  })

  it('để trống thì báo lỗi ngay và không gọi API', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(screen.getByRole('button', { name: /^Đăng nhập$/ }))
    expect(await screen.findByText('Vui lòng nhập email')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('dược sĩ đăng nhập xong vào khu nhân viên; phiên có quyền, vai trò và gợi ý loại phiên', async () => {
    POST.mockResolvedValueOnce(ok(nhanVien('PHARMACIST')))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi, '  lan@example.com  ')
    expect(await screen.findByText('Khu nhân viên')).toBeInTheDocument()
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/auth/dang-nhap', { body: { email: 'lan@example.com', mat_khau: 'Matkhau123' } })
    const p = usePhien.getState()
    expect([p.loai, p.accessToken, p.phaiDoiMatKhau]).toEqual(['noi_bo', 'tok-nv', false])
    expect(p.hoSo?.vaiTro).toBe('PHARMACIST')
    expect(p.quyen).toEqual({ 'profile.self': 'day_du', 'order.view': 'day_du' })
    expect(localStorage.getItem('phien_goi_y')).toBe('noi_bo')
    expect(JSON.stringify({ ...localStorage })).not.toContain('tok-nv')
  })

  it('Admin đăng nhập xong vào khu quản trị', async () => {
    POST.mockResolvedValueOnce(ok(nhanVien('ADMIN')))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi)
    expect(await screen.findByText('Khu quản trị')).toBeInTheDocument()
  })

  it('quay lại trang đang định vào (state.tu) nếu là đường dẫn nội bộ', async () => {
    POST.mockResolvedValueOnce(ok(nhanVien('PHARMACIST')))
    const nguoi = userEvent.setup()
    dung({ tu: '/nhan-vien/don-hang' })
    await dangNhap(nguoi)
    expect(await screen.findByText('Trang đơn hàng')).toBeInTheDocument()
  })

  it.each(['https://trang-lua-dao.example', '//trang-lua-dao.example', '/\\trang-lua-dao.example'])(
    'state.tu=%s không phải đường dẫn nội bộ thì bỏ qua',
    async (tu) => {
      POST.mockResolvedValueOnce(ok(nhanVien('WAREHOUSE')))
      const nguoi = userEvent.setup()
      dung({ tu })
      await dangNhap(nguoi)
      expect(await screen.findByText('Khu nhân viên')).toBeInTheDocument()
    },
  )

  it('tài khoản bị bắt đổi mật khẩu thì sang trang tài khoản, kể cả khi có state.tu', async () => {
    POST.mockResolvedValueOnce(ok(nhanVien('ADMIN', true)))
    const nguoi = userEvent.setup()
    dung({ tu: '/nhan-vien/don-hang' })
    await dangNhap(nguoi)
    expect(await screen.findByText('Trang tài khoản')).toBeInTheDocument()
    expect(usePhien.getState().phaiDoiMatKhau).toBe(true)
  })

  it('sai thông tin: hiện thông điệp, xóa ô mật khẩu, không đăng nhập', async () => {
    POST.mockResolvedValueOnce(loi(401, 'SAI_THONG_TIN_DANG_NHAP', 'Email hoặc mật khẩu không đúng'))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi)
    expect(await screen.findByText('Email hoặc mật khẩu không đúng')).toBeInTheDocument()
    expect(screen.getByLabelText('Mật khẩu')).toHaveValue('')
    expect(screen.getByLabelText('Email')).toHaveValue('lan@example.com')
    expect(usePhien.getState().loai).toBeNull()
  })

  it('khóa tạm: nói rõ phải chờ bao nhiêu phút', async () => {
    POST.mockResolvedValueOnce(loi(403, 'TAI_KHOAN_BI_KHOA', 'Tài khoản bị khóa tạm do nhập sai nhiều lần', { thu_lai_sau_giay: 900 }))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi)
    expect(await screen.findByText(/Hãy thử lại sau 15 phút/)).toBeInTheDocument()
  })

  it('mất mạng: báo không kết nối được', async () => {
    POST.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const nguoi = userEvent.setup()
    dung()
    await dangNhap(nguoi)
    expect(await screen.findByText(/Không kết nối được máy chủ/)).toBeInTheDocument()
  })

  it('đã đăng nhập nội bộ thì vào trang này sẽ được chuyển đi luôn', async () => {
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'WAREHOUSE' }, quyen: {} })
    dung()
    expect(await screen.findByText('Khu nhân viên')).toBeInTheDocument()
    expect(screen.queryByLabelText('Email')).not.toBeInTheDocument()
  })

  it('phiên khách không được coi là đã đăng nhập nội bộ', async () => {
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'khach', hoSo: { id: 1, hoTen: 'Khách' }, quyen: {} })
    dung()
    expect(screen.getByRole('heading', { name: 'Đăng nhập nội bộ' })).toBeInTheDocument()
  })

  it('đang khôi phục phiên thì chưa hiện form (tránh nhấp nháy rồi chuyển trang)', () => {
    usePhien.setState({ daKhoiPhuc: false })
    dung()
    expect(screen.queryByLabelText('Email')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Đang kiểm tra phiên đăng nhập')).toBeInTheDocument()
  })
})
