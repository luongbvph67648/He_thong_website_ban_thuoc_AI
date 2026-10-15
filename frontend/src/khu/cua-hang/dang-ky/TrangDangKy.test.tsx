import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TrangDangKy from './TrangDangKy'

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
        <TrangDangKy />
      </MemoryRouter>
    </ConfigProvider>,
  )
}

const o = (nhan: RegExp | string) => screen.getByLabelText(nhan)

async function sangBuoc2(nguoi: ReturnType<typeof userEvent.setup>, sdt = '0912 345 678') {
  POST.mockResolvedValueOnce(ok({ da_gui: true, het_han_giay: 300 }))
  await nguoi.type(o(/Số điện thoại/), sdt)
  await nguoi.click(screen.getByRole('button', { name: /Gửi mã xác thực/ }))
  await screen.findByLabelText(/Mã xác thực/)
}

async function dienBuoc2(
  nguoi: ReturnType<typeof userEvent.setup>,
  { otp = '123456', ten = 'Nguyễn Văn A', email = '', mk = 'Matkhau123', xn, dongY = true }: {
    otp?: string
    ten?: string
    email?: string
    mk?: string
    xn?: string
    dongY?: boolean
  } = {},
) {
  await nguoi.type(o(/Mã xác thực/), otp)
  await nguoi.type(o(/Họ và tên/), ten)
  if (email) await nguoi.type(o(/Email/), email)
  await nguoi.type(o(/^Mật khẩu/), mk)
  await nguoi.type(o(/Nhập lại mật khẩu/), xn ?? mk)
  if (dongY) await nguoi.click(o(/Tôi đồng ý/))
}

describe('TrangDangKy', () => {
  beforeEach(() => POST.mockReset())
  afterEach(() => vi.useRealTimers())

  it('bước 1 chỉ hiện ô số điện thoại', () => {
    dung()
    expect(screen.getByRole('heading', { name: 'Đăng ký tài khoản' })).toBeInTheDocument()
    expect(o(/Số điện thoại/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/Mã xác thực/)).not.toBeInTheDocument()
  })

  it('số điện thoại sai thì báo lỗi ngay và không gọi API', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.type(o(/Số điện thoại/), '0212345678')
    await nguoi.click(screen.getByRole('button', { name: /Gửi mã xác thực/ }))
    expect(await screen.findByText(/Số điện thoại không hợp lệ/)).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('gửi số đã chuẩn hóa, sang bước 2 và nhắc số vừa nhập', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi, '+84 912 345 678')
    expect(POST).toHaveBeenCalledWith('/api/v1/auth/otp', {
      body: { so_dien_thoai: '0912345678', muc_dich: 'dang_ky' },
    })
    expect(screen.getByText(/0912345678/)).toBeInTheDocument()
  })

  it('bước 1: bị giới hạn tần suất thì cho biết phải chờ bao lâu', async () => {
    POST.mockResolvedValueOnce(loi(429, 'QUA_GIOI_HAN', 'Bạn yêu cầu mã quá nhiều lần', { thu_lai_sau_giay: 1500 }))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.type(o(/Số điện thoại/), '0912345678')
    await nguoi.click(screen.getByRole('button', { name: /Gửi mã xác thực/ }))
    expect(await screen.findByText(/thử lại sau 25 phút/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/Mã xác thực/)).not.toBeInTheDocument()
  })

  it('bước 1: lỗi mạng hiện thông báo chung, không văng lỗi', async () => {
    POST.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const nguoi = userEvent.setup()
    dung()
    await nguoi.type(o(/Số điện thoại/), '0912345678')
    await nguoi.click(screen.getByRole('button', { name: /Gửi mã xác thực/ }))
    expect(await screen.findByText(/Không kết nối được máy chủ/)).toBeInTheDocument()
  })

  it('bước 2: kiểm tra mật khẩu, xác nhận mật khẩu, họ tên và đồng ý chính sách trước khi gọi API', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockClear()
    await nguoi.type(o(/Mã xác thực/), '12345')
    await nguoi.type(o(/^Mật khẩu/), 'abcdefgh')
    await nguoi.type(o(/Nhập lại mật khẩu/), 'khac')
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    expect(await screen.findByText(/Mã gồm 6 chữ số/)).toBeInTheDocument()
    expect(screen.getByText(/Vui lòng nhập họ và tên/)).toBeInTheDocument()
    expect(screen.getByText(/tối thiểu 8 ký tự, gồm cả chữ và số/)).toBeInTheDocument()
    expect(screen.getByText(/Mật khẩu nhập lại không khớp/)).toBeInTheDocument()
    expect(screen.getByText(/Bạn cần đồng ý/)).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('email sai định dạng bị báo, để trống thì hợp lệ', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    await dienBuoc2(nguoi, { email: 'khong-phai-email' })
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    expect(await screen.findByText(/Email không hợp lệ/)).toBeInTheDocument()
  })

  it('đăng ký thành công: gửi đúng dữ liệu (email trống thành null) rồi hiện kết quả và liên kết đăng nhập', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(ok({ id: 1, ho_ten: 'Nguyễn Văn A', so_dien_thoai: '0912345678', email: null }))
    await dienBuoc2(nguoi, { ten: '  Nguyễn Văn A  ' })
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    expect(await screen.findByText('Đăng ký thành công')).toBeInTheDocument()
    expect(POST).toHaveBeenLastCalledWith('/api/v1/auth/dang-ky', {
      body: {
        so_dien_thoai: '0912345678',
        otp: '123456',
        mat_khau: 'Matkhau123',
        ho_ten: 'Nguyễn Văn A',
        email: null,
        dong_y_chinh_sach: true,
      },
    })
    expect(screen.getByRole('link', { name: /Đăng nhập/ })).toHaveAttribute('href', '/dang-nhap')
  })

  it('có email thì gửi email đã cắt khoảng trắng', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(ok({ id: 1, ho_ten: 'A', so_dien_thoai: '0912345678', email: 'a@b.vn' }))
    await dienBuoc2(nguoi, { email: ' a@b.vn ' })
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    await screen.findByText('Đăng ký thành công')
    expect(POST.mock.lastCall?.[1].body.email).toBe('a@b.vn')
  })

  it('mã OTP sai: nói còn mấy lần thử, ở lại bước 2 và giữ nguyên dữ liệu đã nhập', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(loi(422, 'OTP_SAI', 'Mã OTP không đúng', { so_lan_con_lai: 3 }))
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    expect(await screen.findByText(/Mã OTP không đúng.*còn 3 lần thử/)).toBeInTheDocument()
    expect(o(/Họ và tên/)).toHaveValue('Nguyễn Văn A')
    expect(screen.queryByText('Đăng ký thành công')).not.toBeInTheDocument()
  })

  it('hết lượt thử thì hướng dẫn xin mã mới', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(loi(422, 'OTP_SAI', 'Bạn đã nhập sai quá số lần cho phép, vui lòng xin mã mới', { so_lan_con_lai: 0 }))
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    expect(await screen.findByText(/xin mã mới/)).toBeInTheDocument()
  })

  it('mã hết hạn: báo rõ và cho xin mã mới', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(loi(422, 'OTP_HET_HAN', 'Mã OTP đã hết hạn, vui lòng xin mã mới'))
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    expect(await screen.findByText(/đã hết hạn/)).toBeInTheDocument()
  })

  it('email đã dùng: hiện lỗi ngay dưới ô email', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(loi(409, 'TRUNG_DU_LIEU', 'Thông tin này đã được dùng cho một tài khoản khác', { truong: 'email' }))
    await dienBuoc2(nguoi, { email: 'a@b.vn' })
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    const loiEmail = await screen.findByText(/đã được dùng cho một tài khoản khác/)
    expect(loiEmail.closest('.ant-form-item')).toContainElement(o(/Email/))
  })

  it('lỗi validate của server gắn vào đúng trường', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(
      loi(400, 'DU_LIEU_KHONG_HOP_LE', 'Dữ liệu không hợp lệ', [{ truong: 'ho_ten', loi: 'Quá dài' }]),
    )
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    const mucLoi = await screen.findByText('Quá dài')
    expect(mucLoi.closest('.ant-form-item')).toContainElement(o(/Họ và tên/))
  })

  it('lỗi hệ thống hiện thông báo chung', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    POST.mockResolvedValueOnce(loi(500, 'LOI_HE_THONG', 'Lỗi hệ thống, vui lòng thử lại sau', { request_id: 'x' }))
    await dienBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /^Đăng ký$/ }))
    expect(await screen.findByText(/Lỗi hệ thống, vui lòng thử lại sau/)).toBeInTheDocument()
  })

  it('bấm đăng ký hai lần liên tiếp chỉ gửi một request', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    let xong!: (v: unknown) => void
    POST.mockReturnValueOnce(new Promise((giai) => (xong = giai)))
    await dienBuoc2(nguoi)
    const nut = screen.getByRole('button', { name: /^Đăng ký$/ })
    await nguoi.click(nut)
    await nguoi.click(nut)
    expect(POST).toHaveBeenCalledTimes(2) // 1 lần OTP ở bước 1 + 1 lần đăng ký
    xong(ok({ id: 1, ho_ten: 'A', so_dien_thoai: '0912345678', email: null }))
    await screen.findByText('Đăng ký thành công')
  })

  it('gửi lại mã: bị khóa 60 giây đầu, hết thời gian thì bấm được và gửi lại đúng số', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const nguoi = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    dung()
    await sangBuoc2(nguoi)
    const nut = screen.getByRole('button', { name: /Gửi lại mã/ })
    expect(nut).toBeDisabled()
    expect(nut).toHaveTextContent('60')

    await vi.advanceTimersByTimeAsync(61_000)
    await waitFor(() => expect(screen.getByRole('button', { name: /Gửi lại mã/ })).toBeEnabled())

    POST.mockResolvedValueOnce(ok({ da_gui: true, het_han_giay: 300 }))
    await nguoi.click(screen.getByRole('button', { name: /Gửi lại mã/ }))
    expect(POST).toHaveBeenLastCalledWith('/api/v1/auth/otp', { body: { so_dien_thoai: '0912345678', muc_dich: 'dang_ky' } })
    await waitFor(() => expect(screen.getByRole('button', { name: /Gửi lại mã/ })).toBeDisabled())
  })

  it('đổi số điện thoại: quay về bước 1', async () => {
    const nguoi = userEvent.setup()
    dung()
    await sangBuoc2(nguoi)
    await nguoi.click(screen.getByRole('button', { name: /Đổi số điện thoại/ }))
    expect(await screen.findByRole('button', { name: /Gửi mã xác thực/ })).toBeInTheDocument()
    expect(within(document.body).queryByLabelText(/Mã xác thực/)).not.toBeInTheDocument()
  })
})
