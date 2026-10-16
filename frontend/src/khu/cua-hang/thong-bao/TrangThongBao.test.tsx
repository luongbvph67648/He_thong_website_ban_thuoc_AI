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
const TB = { id: 3, loai: 'don_hang', tieu_de: 'Đơn DH1 đã giao thành công', noi_dung: null, lien_ket: '/tai-khoan/don-hang/DH1', da_doc: false, created_at: '2026-10-16T03:00:00Z' }

beforeEach(() => {
  GET.mockReset(); POST.mockReset()
  GET.mockImplementation(async (d: string) => (d === '/api/v1/toi/thong-bao/so-chua-doc' ? ok({ so_chua_doc: 1 }) : d === '/api/v1/toi/thong-bao' ? ok({ du_lieu: [TB], tong: 1, trang: 1, kich_thuoc: 20 }) : d === '/api/v1/toi/gio-hang' ? ok({ dong: [], tam_tinh: '0.00', tong_so_luong: 0 }) : ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 20 })))
  POST.mockResolvedValue(ok({}))
})

describe('Thông báo của khách (KTV13)', () => {
  it('hiện thông báo, bấm vào thì đánh dấu đã đọc và chuyển tới đơn', async () => {
    const { router } = renderTai('/tai-khoan/thong-bao', { loai: 'khach' })
    const u = userEvent.setup()
    await u.click(await screen.findByText('Đơn DH1 đã giao thành công'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/toi/thong-bao/{thong_bao_id}/da-doc')
    await waitFor(() => expect(router.state.location.pathname).toBe('/tai-khoan/don-hang/DH1'))
  })
})
