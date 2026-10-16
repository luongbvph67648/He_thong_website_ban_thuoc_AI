import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
const DELETE = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: vi.fn(), DELETE: (...a: unknown[]) => DELETE(...a) },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const dc = (id: number, mac_dinh: boolean) => ({
  id, ten_nguoi_nhan: `Người ${id}`, so_dien_thoai: '0912345678', dia_chi_chi_tiet: '12 Phố Huế',
  ma_tinh: '201', ten_tinh: 'Hà Nội', ma_phuong_xa: '2010101', ten_phuong_xa: 'Phường Hoàn Kiếm', la_mac_dinh: mac_dinh,
})

beforeEach(() => {
  for (const m of [GET, POST, DELETE]) m.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/toi/dia-chi') return ok([dc(1, true), dc(2, false)])
    if (duong === '/api/v1/dia-gioi/tinh') return ok([{ ma: '201', ten: 'Hà Nội' }])
    if (duong === '/api/v1/dia-gioi/tinh/{ma_tinh}/xa') return ok([{ ma: '2010101', ten: 'Phường Hoàn Kiếm' }])
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('Sổ địa chỉ (trang tài khoản)', () => {
  it('khách chưa đăng nhập bị chuyển tới trang đăng nhập', async () => {
    const { router } = renderTai('/tai-khoan')
    await waitFor(() => expect(router.state.location.pathname).toBe('/dang-nhap'))
  })

  it('hiện địa chỉ, nhãn Mặc định; đặt mặc định và xóa gọi đúng API', async () => {
    POST.mockResolvedValue(ok(dc(2, true)))
    DELETE.mockResolvedValue({ response: { ok: true, status: 204 } })
    renderTai('/tai-khoan', { loai: 'khach' })
    const the = await screen.findAllByTestId('dia-chi')
    expect(the).toHaveLength(2)
    expect(within(the[0]).getByText('Mặc định')).toBeInTheDocument()
    expect(within(the[0]).getByText(/12 Phố Huế, Phường Hoàn Kiếm, Hà Nội/)).toBeInTheDocument()
    expect(within(the[0]).queryByRole('button', { name: 'Đặt làm mặc định' })).not.toBeInTheDocument()
    const u = userEvent.setup()
    await u.click(within(the[1]).getByRole('button', { name: 'Đặt làm mặc định' }))
    await waitFor(() => expect(POST).toHaveBeenCalledWith('/api/v1/toi/dia-chi/{dia_chi_id}/mac-dinh', { params: { path: { dia_chi_id: 2 } } }))
    await u.click(within(the[1]).getByRole('button', { name: 'Xóa' }))
    await u.click(await waitFor(() => { const n = document.querySelector('.ant-popover .ant-btn-primary'); if (!n) throw new Error('chưa mở'); return n as HTMLElement }))
    await waitFor(() => expect(DELETE).toHaveBeenCalled())
  })

  it('thêm địa chỉ: chọn tỉnh rồi xã, gửi đúng mã, không gửi tên', async () => {
    POST.mockResolvedValue(ok(dc(3, false)))
    renderTai('/tai-khoan', { loai: 'khach' })
    const u = userEvent.setup()
    await u.click(await screen.findByRole('button', { name: 'Thêm địa chỉ' }))
    await u.type(await screen.findByLabelText('Người nhận'), 'Lê C')
    await u.type(screen.getByLabelText('Số điện thoại'), '0987654321')
    await u.type(screen.getByLabelText('Số nhà, đường'), '5 Ngõ Hàng')
    const [tinh, xa] = within(screen.getByRole('dialog')).getAllByRole('combobox')
    await u.click(tinh)
    await u.click(await screen.findByTitle('Hà Nội'))
    await u.click(xa)
    await u.click(await screen.findByTitle('Phường Hoàn Kiếm'))
    await u.click(screen.getByRole('button', { name: 'Lưu' }))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][1].body).toEqual({
      ten_nguoi_nhan: 'Lê C', so_dien_thoai: '0987654321', dia_chi_chi_tiet: '5 Ngõ Hàng', ma_tinh: '201', ma_phuong_xa: '2010101', la_mac_dinh: false,
    })
  })
})
