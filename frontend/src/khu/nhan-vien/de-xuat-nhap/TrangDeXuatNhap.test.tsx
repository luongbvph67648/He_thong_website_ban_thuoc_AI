import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const PUT = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn(), PUT: (...a: unknown[]) => PUT(...a), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const dung = (muc: 'day_du' | 'chi_xem' = 'day_du') =>
  renderTai('/nhan-vien/de-xuat-nhap', { loai: 'noi_bo', vaiTro: 'WAREHOUSE', quyen: { 'forecast.view': muc } as never })
const DONG = (r: object = {}) => ({ id: 5, san_pham_id: 1, sku: 'SKU-1', ten_san_pham: 'Paracetamol 500', don_vi_co_so: 'viên', ky_bat_dau: '2026-10-12', ky_ket_thuc: '2026-11-10', so_luong_du_bao: 120, ton_kha_dung: 30, ton_toi_thieu: 10, so_luong_de_xuat: 100, mo_hinh: 'holt_winters', sai_so_mape: '23.456', da_xu_ly: false, ...r })
const tuan = (n: number, d0: number) => Array.from({ length: n }, (_, i) => ({ tuan_bat_dau: `2026-0${1 + (i % 9)}-01`, so_luong: d0 + i }))

beforeEach(() => {
  GET.mockReset(); PUT.mockReset()
  GET.mockImplementation(async (d: string) => {
    if (d === '/api/v1/noi-bo/de-xuat-nhap/ky') return ok([{ ky_bat_dau: '2026-10-12', ky_ket_thuc: '2026-11-10', so_san_pham: 4 }])
    if (d === '/api/v1/noi-bo/de-xuat-nhap') return ok({ du_lieu: [DONG()], tong: 1, trang: 1, kich_thuoc: 20 })
    if (d === '/api/v1/noi-bo/de-xuat-nhap/{de_xuat_id}/bieu-do') return ok({ id: 5, ten_san_pham: 'Paracetamol 500', don_vi_co_so: 'viên', mo_hinh: 'holt_winters', lich_su: tuan(26, 5), du_bao: tuan(5, 40) })
    return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
  })
})

describe('Đề xuất nhập từ AI (KHO14)', () => {
  it('hiện đề xuất, mô hình, MAPE; mặc định chỉ sản phẩm cần nhập', async () => {
    dung()
    expect(await screen.findByText('Paracetamol 500')).toBeInTheDocument()
    expect(screen.getByText('100 viên')).toBeInTheDocument()
    expect(screen.getByText('Holt-Winters')).toBeInTheDocument()
    expect(screen.getByText('MAPE 23.5%')).toBeInTheDocument()
    expect(screen.getByText('Chưa xử lý', { selector: '.ant-tag' })).toBeInTheDocument()
    const goi = GET.mock.calls.find((c) => c[0] === '/api/v1/noi-bo/de-xuat-nhap')!
    expect(goi[1].params.query).toMatchObject({ chi_can_nhap: true, trang: 1 })
  })

  it('mở biểu đồ: 31 cột (26 lịch sử + 5 dự báo) và đánh dấu đã xử lý', async () => {
    PUT.mockResolvedValue(ok(DONG({ da_xu_ly: true })))
    dung()
    const u = userEvent.setup()
    await u.click((await screen.findByText('Biểu đồ')).closest('button')!)
    const hinh = await screen.findByLabelText(/Biểu đồ lịch sử xuất và dự báo/)
    expect(hinh.querySelectorAll('rect')).toHaveLength(31)
    await u.click(screen.getByText(/Đánh dấu đã xử lý/).closest('button')!)
    await waitFor(() => expect(PUT).toHaveBeenCalled())
    expect(PUT.mock.calls[0][1]).toMatchObject({ params: { path: { de_xuat_id: 5 } }, body: { da_xu_ly: true } })
  })

  it('Admin chỉ xem: xem được biểu đồ, không có nút đánh dấu', async () => {
    dung('chi_xem')
    const u = userEvent.setup()
    await u.click((await screen.findByText('Biểu đồ')).closest('button')!)
    await screen.findByLabelText(/Biểu đồ lịch sử xuất và dự báo/)
    expect(screen.queryByText(/Đánh dấu đã xử lý/)).not.toBeInTheDocument()
  })

  it('chưa có đề xuất nào thì báo trống', async () => {
    GET.mockImplementation(async (d: string) => (d === '/api/v1/noi-bo/de-xuat-nhap' ? ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 20 }) : ok([])))
    dung()
    expect(await screen.findByText(/Chưa có đề xuất nào/)).toBeInTheDocument()
  })
})
