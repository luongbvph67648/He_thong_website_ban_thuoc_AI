import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: vi.fn(), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const yc = (ma: string, trang_thai: string, ma_don: string | null = null) => ({
  ma_yeu_cau: ma, trang_thai, ho_ten: 'A', so_anh: 1, ghi_chu: null, ly_do_tu_choi: null, ma_don, created_at: '2026-10-16T01:00:00Z',
})
const anh = () => new File([new Uint8Array(10)], 'don.png', { type: 'image/png' })

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/toi/don-thuoc') return ok([yc('YC1', 'cho_duyet'), yc('YC2', 'da_tao_don', 'DH9'), yc('YC3', 'tu_choi')])
    if (duong === '/api/v1/toi/don-thuoc/{ma_yeu_cau}')
      return ok({ ...yc('YC1', 'cho_duyet'), so_dien_thoai: '0912345678', anh: ['/api/v1/tep-rieng/don-thuoc/x.png?het_han=1&ky=a'] })
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('Gửi đơn thuốc (KVL08, KTV07)', () => {
  it('khách vãng lai phải có ô OTP; thành viên thì không', async () => {
    const { unmount } = renderTai('/gui-don-thuoc')
    expect(await screen.findByPlaceholderText('6 chữ số')).toBeInTheDocument()
    unmount()
    renderTai('/gui-don-thuoc', { loai: 'khach' })
    await screen.findByRole('button', { name: 'Gửi đơn thuốc' })
    expect(screen.queryByPlaceholderText('6 chữ số')).not.toBeInTheDocument()
  })

  it('thành viên gửi ảnh: gọi POST /don-thuoc rồi hiện mã yêu cầu', async () => {
    POST.mockResolvedValue(ok({ ma_yeu_cau: 'YC123', trang_thai: 'cho_duyet', created_at: '2026-10-16T01:00:00Z' }))
    renderTai('/gui-don-thuoc', { loai: 'khach' })
    const o = await screen.findByLabelText('Họ tên người bệnh')
    await userEvent.type(o, 'Nguyễn A')
    await userEvent.type(screen.getByLabelText('Số điện thoại liên hệ'), '0912345678')
    await userEvent.upload(document.querySelector('input[type=file]') as HTMLInputElement, anh())
    await userEvent.click(screen.getByRole('button', { name: 'Gửi đơn thuốc' }))
    expect(await screen.findByText(/YC123/)).toBeInTheDocument()
    expect(POST.mock.calls[0][0]).toBe('/api/v1/don-thuoc')
    const fd = POST.mock.calls[0][1].bodySerializer() as FormData
    expect(fd.getAll('anh')).toHaveLength(1)
    expect(fd.get('so_dien_thoai')).toBe('0912345678')
    expect(fd.has('otp')).toBe(false)
  })

  it('không có ảnh thì không gửi', async () => {
    renderTai('/gui-don-thuoc', { loai: 'khach' })
    await userEvent.type(await screen.findByLabelText('Họ tên người bệnh'), 'A')
    await userEvent.type(screen.getByLabelText('Số điện thoại liên hệ'), '0912345678')
    await userEvent.click(screen.getByRole('button', { name: 'Gửi đơn thuốc' }))
    expect(await screen.findByText('Chọn ít nhất một ảnh')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })
})

describe('Đơn thuốc của tôi (KTV07)', () => {
  it('chưa đăng nhập thì chuyển tới đăng nhập', async () => {
    const { router } = renderTai('/tai-khoan/don-thuoc')
    await waitFor(() => expect(router.state.location.pathname).toBe('/dang-nhap'))
  })

  it('liệt kê trạng thái, link đơn hàng; xem chi tiết có ảnh và hủy được khi chờ duyệt', async () => {
    POST.mockResolvedValue(ok(yc('YC1', 'khach_huy')))
    renderTai('/tai-khoan/don-thuoc', { loai: 'khach' })
    expect(await screen.findByText('Chờ duyệt')).toBeInTheDocument()
    expect(screen.getByText('Đã tạo đơn hàng')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'DH9' })).toHaveAttribute('href', '/tai-khoan/don-hang/DH9')
    await userEvent.click(screen.getAllByRole('button', { name: 'Chi tiết' })[0])
    expect(await screen.findByAltText('Ảnh đơn thuốc')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Hủy yêu cầu' }))
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Hủy yêu cầu' })).toHaveLength(2))
    await userEvent.click(screen.getAllByRole('button', { name: 'Hủy yêu cầu' })[1])
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/toi/don-thuoc/{ma_yeu_cau}/huy')
  })
})
