import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangKiemKe from './TrangKiemKe'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
const PUT = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: (...a: unknown[]) => PUT(...a), DELETE: vi.fn() } }))
let daChot = false
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })

const NV = { id: 1, ma_nhan_vien: 'NV0001', ho_ten: 'Kho Một' }
const TOM = { id: 4, ma_phieu: 'KK26000004', danh_muc: null, nhan_vien: NV, trang_thai: 'dang_kiem', thoi_diem_chup_ton: '2026-10-16T01:00:00Z', chot_luc: null, so_dong: 1, so_dong_lech: 0 }
const dong = (tt: number | null) => ({ lo_id: 9, san_pham: { id: 3, sku: 'PARA', ten: 'Paracetamol' }, so_lo: 'L01', han_su_dung: '2027-01-01', so_luong_so_sach: 10, so_luong_thuc_te: tt, chenh_lech: tt === null ? null : tt - 10 })

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  PUT.mockReset()
  daChot = false
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/kiem-ke') return ok({ du_lieu: [TOM], tong: 1, trang: 1, kich_thuoc: 20 })
    if (duong === '/api/v1/noi-bo/kiem-ke/{phieu_id}') return ok(daChot ? { ...TOM, trang_thai: 'da_chot', so_dong_lech: 1, chot_luc: '2026-10-16T02:00:00Z', dong: [dong(8)] } : { ...TOM, dong: [dong(null)] })
    if (duong === '/api/v1/danh-muc') return ok([])
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('TrangKiemKe', () => {
  it('nhập số thực tế, chốt, rồi lập phiếu điều chỉnh từ dòng lệch', async () => {
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'K', vaiTro: 'WAREHOUSE' }, quyen: { 'stocktake.manage': 'day_du' } })
    PUT.mockResolvedValue(ok({ ...TOM, dong: [dong(8)], so_dong_lech: 1 }))
    POST.mockImplementation(async (duong: string) => {
      if (duong.endsWith('/chot')) daChot = true
      return duong.endsWith('/chot') ? ok({ ...TOM, trang_thai: 'da_chot', so_dong_lech: 1, chot_luc: '2026-10-16T02:00:00Z', dong: [dong(8)] }) : ok({ ma_phieu: 'DC26000001' })
    })
    render(
      <ConfigProvider locale={viVN}>
        <App>
          <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
            <MemoryRouter>
              <TrangKiemKe />
            </MemoryRouter>
          </QueryClientProvider>
        </App>
      </ConfigProvider>,
    )
    const u = userEvent.setup()
    await u.click(await screen.findByText('KK26000004'))
    const o = await screen.findByLabelText('Thực tế L01')
    await u.clear(o)
    await u.type(o, '8')
    await u.click(screen.getByRole('button', { name: /Chốt kiểm kê/ }))
    await u.click(await screen.findByRole('button', { name: /^Chốt$/ }))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(1))
    expect(PUT.mock.calls[0][1].body).toEqual({ dong: [{ lo_id: 9, so_luong_thuc_te: 8 }] })
    await u.click(await screen.findByRole('button', { name: /Lập phiếu điều chỉnh/ }))
    await waitFor(() => expect(POST.mock.calls.some((c) => c[0] === '/api/v1/noi-bo/dieu-chinh')).toBe(true))
    expect(POST.mock.calls.find((c) => c[0] === '/api/v1/noi-bo/dieu-chinh')?.[1].body.phieu_kiem_ke_id).toBe(4)
  })
})
