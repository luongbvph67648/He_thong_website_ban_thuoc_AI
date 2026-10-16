import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'
import { useGioCucBo } from './gioHang'

vi.setConfig({ testTimeout: 60_000 })
const GET = vi.fn()
const POST = vi.fn()
const PUT = vi.fn()
const DELETE = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: (...a: unknown[]) => PUT(...a), DELETE: (...a: unknown[]) => DELETE(...a) },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const DV = (id: number, ten: string, he_so: number, gia: string) => ({ id, ten_don_vi: ten, he_so, gia_ban: gia })
const dong = (kw: Record<string, unknown> = {}) => ({
  dong_id: 11,
  san_pham: { id: 1, ten: 'Paracetamol', slug: 'paracetamol', anh_chinh_url: null, can_tu_van: false },
  don_vi: DV(5, 'viên', 1, '1000.00'),
  don_vi_co_the_chon: [DV(5, 'viên', 1, '1000.00'), DV(6, 'hộp', 10, '9500.00')],
  so_luong: 2, thanh_tien: '2000.00', toi_da_don_vi: 20, ton_kha_dung_don_vi: 100, mua_duoc: true, ly_do: null, ...kw,
})
const gio = (d: unknown[], tam = '2000.00') => ({ dong: d, tam_tinh: tam, tong_so_luong: d.length })
const dsDong = () => ({ dong: [dong()], tam_tinh: '2000.00', tong_so_luong: 2 })

beforeEach(() => {
  for (const m of [GET, POST, PUT, DELETE]) m.mockReset()
  localStorage.clear()
  useGioCucBo.setState({ dong: [] })
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/toi/gio-hang') return ok(dsDong())
    if (duong === '/api/v1/gio-hang/mua-kem') return ok([])
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('TrangGioHang', () => {
  it('thành viên: hiện dòng, tạm tính; đổi số lượng và xóa gọi API của giỏ tài khoản', async () => {
    PUT.mockResolvedValue(ok(gio([dong({ so_luong: 5, thanh_tien: '5000.00' })], '5000.00')))
    DELETE.mockResolvedValue(ok(gio([], '0.00')))
    renderTai('/gio-hang', { loai: 'khach' })
    expect(await screen.findByRole('link', { name: 'Paracetamol' })).toBeInTheDocument()
    expect(screen.getByText(/Tạm tính: 2\.000/)).toBeInTheDocument()
    const u = userEvent.setup()
    const o = screen.getByLabelText('Số lượng Paracetamol')
    await u.clear(o)
    await u.type(o, '5')
    await u.tab()
    await waitFor(() => expect(PUT).toHaveBeenCalled())
    expect(PUT.mock.calls[0][0]).toBe('/api/v1/toi/gio-hang/dong/{dong_id}')
    expect(PUT.mock.calls[0][1].body).toEqual({ so_luong: 5 })
    await u.click(screen.getByRole('button', { name: 'Xóa Paracetamol' }))
    await waitFor(() => expect(DELETE).toHaveBeenCalled())
    expect(await screen.findByText('Giỏ hàng trống')).toBeInTheDocument()
  })

  it('dòng không còn mua được (thuốc kê đơn) hiện nhãn, khóa thanh toán', async () => {
    GET.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/toi/gio-hang') return ok(gio([dong({ mua_duoc: false, ly_do: 'thuoc_ke_don' })], '0.00'))
      if (duong === '/api/v1/danh-muc') return ok([])
      return ok([])
    })
    renderTai('/gio-hang', { loai: 'khach' })
    expect(await screen.findByText('Thuốc kê đơn: không mua online')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tiến hành thanh toán' })).toBeDisabled()
  })

  it('khách vãng lai: dựng giỏ từ localStorage qua /gio-hang/xem, mời đăng nhập để thanh toán', async () => {
    localStorage.setItem('gio_hang_khach', JSON.stringify([{ san_pham_id: 1, don_vi_id: 5, so_luong: 2 }]))
    useGioCucBo.setState({ dong: [{ san_pham_id: 1, don_vi_id: 5, so_luong: 2 }] })
    POST.mockResolvedValue(ok(gio([dong({ dong_id: null })])))
    renderTai('/gio-hang')
    expect(await screen.findByRole('link', { name: 'Paracetamol' })).toBeInTheDocument()
    expect(POST.mock.calls[0][0]).toBe('/api/v1/gio-hang/xem')
    expect(POST.mock.calls[0][1].body).toEqual({ dong: [{ san_pham_id: 1, don_vi_id: 5, so_luong: 2 }] })
    expect(screen.getByRole('button', { name: 'Đăng nhập để thanh toán' })).toBeInTheDocument()
  })

  it('"Thường được mua cùng" hiện khi có gợi ý và ẩn khi rỗng', async () => {
    GET.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/toi/gio-hang') return ok(dsDong())
      if (duong === '/api/v1/gio-hang/mua-kem') return ok([{ id: 9, ten: 'Vitamin C', slug: 'vitamin-c', anh_chinh_url: null, don_vi_id: 3, ten_don_vi: 'ống', gia_ban: '5000.00' }])
      return ok([])
    })
    renderTai('/gio-hang', { loai: 'khach' })
    expect(await screen.findByRole('heading', { name: 'Thường được mua cùng' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Vitamin C' })).toBeInTheDocument()
  })

  it('không có gợi ý thì không hiện mục "Thường được mua cùng"', async () => {
    renderTai('/gio-hang', { loai: 'khach' })
    await screen.findByRole('link', { name: 'Paracetamol' })
    expect(screen.queryByText('Thường được mua cùng')).not.toBeInTheDocument()
  })
})
