import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../stores/phien'
import { renderTai } from '../../test/render'

const POST = vi.fn()
vi.mock('../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../api/client')>()),
  api: { POST: (...tham_so: unknown[]) => POST(...tham_so), GET: vi.fn() },
}))

describe('CuaHangLayout: đăng xuất', () => {
  beforeEach(() => {
    POST.mockReset()
    localStorage.clear()
  })

  it('đăng xuất gọi API thu hồi phiên, xóa phiên trong bộ nhớ và gợi ý, rồi về trang chủ', async () => {
    POST.mockResolvedValueOnce({ response: { status: 204 } })
    const { router } = renderTai('/gio-hang', { loai: 'khach' })
    await userEvent.setup().click(await screen.findByRole('button', { name: /Đăng xuất/ }))

    await waitFor(() => expect(usePhien.getState().loai).toBeNull())
    expect(POST).toHaveBeenCalledWith('/api/v1/auth/dang-xuat')
    expect(usePhien.getState().accessToken).toBeNull()
    expect(localStorage.getItem('phien_goi_y')).toBeNull()
    expect(router.state.location.pathname).toBe('/')
    expect(await screen.findByRole('link', { name: /Đăng nhập/ })).toHaveAttribute('href', '/dang-nhap')
  })

  it('mất mạng khi đăng xuất vẫn xóa phiên phía trình duyệt', async () => {
    POST.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    renderTai('/', { loai: 'khach' })
    await userEvent.setup().click(await screen.findByRole('button', { name: /Đăng xuất/ }))
    await waitFor(() => expect(usePhien.getState().loai).toBeNull())
  })

  it('trong lúc đang lấy lại phiên không hiện nhầm "Đăng nhập"', async () => {
    renderTai('/')
    act(() => usePhien.setState({ daKhoiPhuc: false }))
    expect(await screen.findByRole('status', { name: 'Đang tải tài khoản' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Đăng nhập/ })).not.toBeInTheDocument()
    act(() => usePhien.setState({ daKhoiPhuc: true }))
    expect(await screen.findByRole('link', { name: /Đăng nhập/ })).toBeInTheDocument()
  })
})
