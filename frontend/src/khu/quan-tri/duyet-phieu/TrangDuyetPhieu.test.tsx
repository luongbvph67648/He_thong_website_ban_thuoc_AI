import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangDuyetPhieu from './TrangDuyetPhieu'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a) } }))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string) => ({ error: { ma_loi, thong_diep, chi_tiet: null }, response: { ok: false, status } })

const NV = { id: 5, ma_nhan_vien: 'NV0005', ho_ten: 'Kho Một' }
const CHO = { loai: 'huy', id: 9, ma_phieu: 'PH26000009', ly_do: 'het_han', trang_thai_duyet: 'cho_duyet', nguoi_lap: NV, created_at: '2026-10-01T00:00:00Z', so_dong: 1 }
const CT = {
  ...CHO,
  mo_ta: null,
  nguoi_duyet: null,
  ly_do_tu_choi: null,
  duyet_luc: null,
  dong: [{ lo_id: 3, san_pham: { id: 1, sku: 'PARA', ten: 'Paracetamol' }, so_lo: 'L1', han_su_dung: '2026-12-01', tu_khu: 'kho_ban', so_luong: 4 }],
}

function dung(quyen: Record<string, 'day_du' | 'chi_xem'>) {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <MemoryRouter><TrangDuyetPhieu /></MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/duyet-phieu') return ok({ du_lieu: [CHO], tong: 1, trang: 1, kich_thuoc: 20 })
    if (duong === '/api/v1/noi-bo/duyet-phieu/{loai}/{phieu_id}') return ok(CT)
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('TrangDuyetPhieu', () => {
  it('lọc mặc định theo chờ duyệt và gọi API với loại, trạng thái', async () => {
    dung({ 'stock_doc.approve': 'day_du' })
    expect(await screen.findByText('PH26000009')).toBeInTheDocument()
    expect(GET.mock.calls[0][1].params.query.trang_thai_duyet).toBe('cho_duyet')
  })

  it('hiện lỗi tự duyệt của backend và không đóng phiếu', async () => {
    POST.mockResolvedValue(loi(403, 'TU_DUYET_KHONG_DUOC', 'Người lập phiếu không được tự duyệt'))
    dung({ 'stock_doc.approve': 'day_du' })
    await userEvent.click(await screen.findByText('PH26000009'))
    await userEvent.click(await screen.findByRole('button', { name: 'Duyệt' }))
    await userEvent.click(screen.getAllByRole('button', { name: 'Duyệt' }).at(-1) as HTMLElement)
    expect(await screen.findByText(/không được tự duyệt/)).toBeInTheDocument()
  })

  it('từ chối bắt buộc lý do rồi gửi lý do đã cắt khoảng trắng', async () => {
    POST.mockResolvedValue(ok({ ...CT, trang_thai_duyet: 'tu_choi' }))
    dung({ 'stock_doc.approve': 'day_du' })
    await userEvent.click(await screen.findByText('PH26000009'))
    await userEvent.click(await screen.findByRole('button', { name: 'Từ chối' }))
    const hop = await screen.findByPlaceholderText('Lý do từ chối (bắt buộc)')
    await userEvent.click(screen.getAllByRole('button', { name: 'Từ chối' }).at(-1) as HTMLElement)
    expect(await screen.findByText('Cần nhập lý do từ chối')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
    await userEvent.type(hop, '  Còn dùng được ')
    await userEvent.click(screen.getAllByRole('button', { name: 'Từ chối' }).at(-1) as HTMLElement)
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][1].body).toEqual({ ly_do: 'Còn dùng được' })
  })

  it('không có quyền ghi thì không thấy nút duyệt', async () => {
    dung({ 'stock_doc.approve': 'chi_xem' })
    await userEvent.click(await screen.findByText('PH26000009'))
    await screen.findByText('Paracetamol (PARA)')
    expect(screen.queryByRole('button', { name: 'Duyệt' })).toBeNull()
  })
})
