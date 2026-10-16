import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangNhaCungCap from './TrangNhaCungCap'
import TrangTaoPhieuNhap from './TrangTaoPhieuNhap'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PATCH: vi.fn(), DELETE: vi.fn() } }))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({ error: { ma_loi, thong_diep, chi_tiet }, response: { ok: false, status } })

const NCC = { id: 3, ten: 'Dược A', ma_so_thue: null, dia_chi: null, nguoi_lien_he: null, so_dien_thoai: null, email: null, dang_hop_tac: true, created_at: '2026-10-01T00:00:00Z', phien_ban: 'a'.repeat(16) }
const SP = { id: 7, sku: 'PARA', ten: 'Paracetamol', don_vi_mac_dinh_id: 21, don_vi: [{ id: 20, ten_don_vi: 'viên', he_so: 1, ma_vach: null }, { id: 21, ten_don_vi: 'hộp', he_so: 100, ma_vach: '893' }] }

function dung(node: React.ReactNode, quyen: Record<string, 'day_du' | 'chi_xem'>) {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'K', vaiTro: 'WAREHOUSE' }, quyen })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <MemoryRouter>{node}</MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/nha-cung-cap') return ok({ du_lieu: [NCC], tong: 1, trang: 1, kich_thuoc: 20 })
    if (duong === '/api/v1/noi-bo/phieu-nhap/tra-cuu-san-pham') return ok([SP])
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('TrangNhaCungCap', () => {
  it('kho thấy nút thêm và sửa; Admin chỉ xem', async () => {
    const { unmount } = dung(<TrangNhaCungCap />, { 'supplier.manage': 'day_du' })
    expect(await screen.findByText('Dược A')).toBeInTheDocument()
    expect(screen.getByText('Thêm nhà cung cấp')).toBeInTheDocument()
    expect(screen.getByText('Sửa')).toBeInTheDocument()
    unmount()
    dung(<TrangNhaCungCap />, { 'supplier.manage': 'chi_xem' })
    expect(await screen.findByText('Dược A')).toBeInTheDocument()
    expect(screen.queryByText('Thêm nhà cung cấp')).not.toBeInTheDocument()
    expect(screen.queryByText('Sửa')).not.toBeInTheDocument()
  })
})

describe('TrangTaoPhieuNhap', () => {
  it('quét mã: một kết quả tự thêm dòng; hạn ngắn hỏi xác nhận rồi gửi lại với xac_nhan_canh_bao', async () => {
    POST.mockResolvedValueOnce(loi(409, 'CAN_XAC_NHAN_CANH_BAO', 'cần xác nhận', { canh_bao: [{ dong: 0, loai: 'han_su_dung_ngan', han_su_dung: '2026-12-01', so_ngay_con_lai: 40, toi_thieu: 180 }] }))
    POST.mockResolvedValueOnce(ok({ ma_phieu: 'PN26000001' }))
    dung(<TrangTaoPhieuNhap />, { 'stock.import': 'day_du' })
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText(/Quét mã vạch/), '893{Enter}')
    expect(await screen.findByText('Paracetamol')).toBeInTheDocument()
    expect(GET.mock.calls.some((c) => c[0] === '/api/v1/noi-bo/phieu-nhap/tra-cuu-san-pham' && c[1].params.query.q === '893')).toBe(true)
    await u.click(screen.getAllByRole('combobox')[0])
    await u.click(await screen.findByText('Dược A'))
    await u.type(screen.getByLabelText('Số lô'), 'lo01')
    await u.type(screen.getByLabelText('Hạn sử dụng'), '2026-12-01')
    await u.type(screen.getByLabelText('Giá nhập'), '60000')
    await u.click(screen.getByRole('button', { name: /Lưu phiếu nhập/ }))
    expect(await screen.findByText(/Dòng 1: còn 40 ngày/)).toBeInTheDocument()
    expect(POST.mock.calls[0][1].body.xac_nhan_canh_bao).toBe(false)
    expect(POST.mock.calls[0][1].body.dong[0]).toMatchObject({ san_pham_id: 7, don_vi_id: 21, so_lo: 'lo01', han_su_dung: '2026-12-01', so_luong: 1, gia_nhap: '60000' })
    await u.click(screen.getByText('Vẫn nhập'))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(2))
    expect(POST.mock.calls[1][1].body.xac_nhan_canh_bao).toBe(true)
  })

  it('nút lưu bị khóa khi chưa đủ thông tin', async () => {
    dung(<TrangTaoPhieuNhap />, { 'stock.import': 'day_du' })
    expect(await screen.findByRole('button', { name: /Lưu phiếu nhập/ })).toBeDisabled()
  })
})
