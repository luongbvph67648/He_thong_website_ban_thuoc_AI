import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TrangQuenMatKhau from './TrangQuenMatKhau'

const POST = vi.fn()
vi.mock('../../../api/client', () => ({ api: { POST: (...tham_so: unknown[]) => POST(...tham_so) } }))

const ok = (data: unknown) => ({ data, response: { status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({
  error: { ma_loi, thong_diep, chi_tiet },
  response: { status },
})

function dung() {
  return render(
    <ConfigProvider locale={viVN}>
      <MemoryRouter>
        <TrangQuenMatKhau />
      </MemoryRouter>
    </ConfigProvider>,
  )
}

type Nguoi = ReturnType<typeof userEvent.setup>
const o = (nhan: RegExp | string) => screen.getByLabelText(nhan)

async function sangBuoc2(nguoi: Nguoi, { sdt = '0912 345 678', email = false } = {}) {
  POST.mockResolvedValueOnce(ok({ da_gui: true, het_han_giay: 300 }))
  await nguoi.type(o(/Số điện thoại/), sdt)
  if (email) await nguoi.click(screen.getByLabelText(/Email đã đăng ký/))
  await nguoi.click(screen.getByRole('button', { name: /Gửi mã xác thực/ }))
  await screen.findByLabelText(/Mã xác thực/)
}

async function dienBuoc2(nguoi: Nguoi, { otp = '123456', mk = 'Matkhaumoi2', xn }: { otp?: string; mk?: string; xn?: string } = {}) {
  await nguoi.type(o(/Mã xác thực/), otp)
  await nguoi.type(o(/^Mật khẩu mới/), mk)
  await nguoi.type(o(/Nhập lại mật khẩu mới/), xn ?? mk)
}

describe('TrangQuenMatKhau', () => {
  beforeEach(() => POST.mockReset())
  afterEach(() => vi.useRealTimers())

  it('bước 1: số điện thoại sai thì báo ngay và không gọi API', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.type(o(/Số điện thoại/), '0212345678')
    await nguoi.click(screen.getByRole('button', { name: /Gửi mã xác thực/ }))
    expect(await screen.findByText(/Số điện thoại không hợp lệ/)).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('mặc định nhận mã qua SMS: gửi số đã chuẩn hóa với mục đích quen_mat_khau', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    expect(POST).toHaveBeenCalledWith('/api/v1/auth/otp', {
      body: { so_dien_thoai: '0912345678', muc_dich: 'quen_mat_khau', kenh: 'sms' },
    })
    expect(screen.getByText(/Nếu số/)).toHaveTextContent('0912345678')
    expect(screen.getByText(/Nếu số/)).toHaveTextContent('tin nhắn SMS')
  })

  it('chọn email thì gửi kenh=email và nói mã gửi qua email', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi, { email: true })
    expect(POST).toHaveBeenCalledWith('/api/v1/auth/otp', {
      body: { so_dien_thoai: '0912345678', muc_dich: 'quen_mat_khau', kenh: 'email' },
    })
    expect(screen.getByText(/Nếu số/)).toHaveTextContent('qua email')
  })

  it('thông báo ở bước 2 không khẳng định số có tài khoản (chống dò tài khoản)', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    expect(screen.getByText(/Nếu số/)).toBeInTheDocument()
    expect(screen.queryByText(/chưa đăng ký|không tồn tại|không có tài khoản/i)).not.toBeInTheDocument()
  })

  it('quá giới hạn xin mã: ở lại bước 1 và nói phải chờ bao lâu', async () => {
    POST.mockResolvedValueOnce(loi(429, 'QUA_GIOI_HAN', 'Bạn yêu cầu mã quá nhiều lần, vui lòng thử lại sau', { thu_lai_sau_giay: 600 }))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.type(o(/Số điện thoại/), '0912345678')
    await nguoi.click(screen.getByRole('button', { name: /Gửi mã xác thực/ }))
    expect(await screen.findByText(/Hãy thử lại sau 10 phút/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/Mã xác thực/)).not.toBeInTheDocument()
  })

  it('bước 2: mật khẩu yếu hoặc nhập lại không khớp thì báo lỗi và không gọi API', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockClear()
    await dienBuoc2(nguoi, { mk: 'chuchuchu', xn: 'khac' })
    await nguoi.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }))
    expect(await screen.findByText(/tối thiểu 8 ký tự, gồm cả chữ và số/)).toBeInTheDocument()
    expect(screen.getByText('Mật khẩu nhập lại không khớp')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('đặt lại thành công: gửi đúng thân yêu cầu và hiện nút đăng nhập', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(ok({ da_dat_lai: true }))
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }))
    expect(await screen.findByText('Đã đặt lại mật khẩu')).toBeInTheDocument()
    expect(POST).toHaveBeenLastCalledWith('/api/v1/auth/dat-lai-mat-khau', {
      body: { so_dien_thoai: '0912345678', otp: '123456', mat_khau_moi: 'Matkhaumoi2' },
    })
    expect(screen.getByRole('link', { name: /Đăng nhập/ })).toHaveAttribute('href', '/dang-nhap')
  })

  it('OTP sai: báo ở ô mã kèm số lần thử còn lại, giữ nguyên các ô khác', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(loi(422, 'OTP_SAI', 'Mã OTP không đúng', { so_lan_con_lai: 3 }))
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }))
    expect(await screen.findByText('Mã OTP không đúng. Bạn còn 3 lần thử.')).toBeInTheDocument()
    expect(o(/^Mật khẩu mới/)).toHaveValue('Matkhaumoi2')
  })

  it('OTP hết lượt thử: chỉ hiện thông điệp, không hứa còn lần thử', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(loi(422, 'OTP_SAI', 'Bạn đã nhập sai quá số lần cho phép, vui lòng xin mã mới', { so_lan_con_lai: 0 }))
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }))
    expect(await screen.findByText('Bạn đã nhập sai quá số lần cho phép, vui lòng xin mã mới')).toBeInTheDocument()
  })

  it('OTP hết hạn', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(loi(422, 'OTP_HET_HAN', 'Mã OTP đã hết hạn, vui lòng xin mã mới'))
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }))
    expect(await screen.findByText('Mã OTP đã hết hạn, vui lòng xin mã mới')).toBeInTheDocument()
  })

  it('lỗi validate của máy chủ gắn vào đúng ô', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(
      loi(400, 'DU_LIEU_KHONG_HOP_LE', 'Dữ liệu không hợp lệ', [{ truong: 'mat_khau_moi', loi: 'Mật khẩu quá yếu' }]),
    )
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /Đặt lại mật khẩu/ }))
    expect(await screen.findByText('Mật khẩu quá yếu')).toBeInTheDocument()
  })

  it('gửi lại mã: khóa 60 giây, hết thời gian thì gửi lại đúng số và đúng kênh', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const nguoi = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    dung()
    await sangBuoc2(nguoi, { email: true })
    expect(screen.getByRole('button', { name: /Gửi lại mã/ })).toBeDisabled()

    await vi.advanceTimersByTimeAsync(61_000)
    await waitFor(() => expect(screen.getByRole('button', { name: /Gửi lại mã/ })).toBeEnabled())
    POST.mockResolvedValueOnce(ok({ da_gui: true, het_han_giay: 300 }))
    await nguoi.click(screen.getByRole('button', { name: /Gửi lại mã/ }))
    expect(POST).toHaveBeenLastCalledWith('/api/v1/auth/otp', {
      body: { so_dien_thoai: '0912345678', muc_dich: 'quen_mat_khau', kenh: 'email' },
    })
  })

  it('đổi số điện thoại: quay về bước 1', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /Đổi số điện thoại/ }))
    expect(await screen.findByRole('button', { name: /Gửi mã xác thực/ })).toBeInTheDocument()
  })
})
