import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangCanhBao from './TrangCanhBao'
import TrangTonKho from './TrangTonKho'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a) } }))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })

let day_du = true
const TON = (): unknown => ({
  du_lieu: [{ san_pham_id: 1, sku: 'PARA', ten: 'Paracetamol', don_vi_co_so: 'viên', ton_kha_dung: 30, ton_toi_thieu: 100, thap: true, tong_ton: day_du ? 57 : null, tong_giu: day_du ? 3 : null, tong_biet_tru: day_du ? 2 : null, so_lo: 1 }],
  tong: 1, trang: 1, kich_thuoc: 20,
})
const LO = (): unknown => [{ lo_id: 5, so_lo: 'L01', ngay_san_xuat: null, han_su_dung: '2027-01-01', trang_thai: 'dang_ban', kha_dung: 30, so_luong_ton: day_du ? 30 : null, so_luong_giu: day_du ? 0 : null, so_luong_biet_tru: day_du ? 0 : null, gia_nhap: day_du ? '700.00' : null }]

function dung(node: React.ReactNode) {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'K', vaiTro: 'WAREHOUSE' }, quyen: { 'stock.view': 'day_du', 'stock.alert.view': 'day_du' } })
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
  day_du = true
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/ton-kho') return ok(TON())
    if (duong === '/api/v1/noi-bo/ton-kho/{san_pham_id}/lo') return ok(LO())
    if (duong === '/api/v1/noi-bo/canh-bao-kho')
      return ok({ ton_thap: { tong: 1, du_lieu: [{ san_pham_id: 1, sku: 'PARA', ten: 'Paracetamol', ton_kha_dung: 30, ton_toi_thieu: 100 }] }, can_han: { tong: 0, du_lieu: [] }, het_han: { tong: 2, du_lieu: [] } })
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('TrangTonKho', () => {
  it('kho: hiện tổng tồn, mở rộng ra lô có giá nhập', async () => {
    dung(<TrangTonKho />)
    expect(await screen.findByText('Tồn thấp')).toBeInTheDocument()
    expect(screen.getByText('Tổng tồn')).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: /Mở rộng|expand/i }))
    expect(await screen.findByText('L01')).toBeInTheDocument()
    expect(screen.getByText('Giá nhập')).toBeInTheDocument()
  })
  it('dược sĩ: backend ẩn số liệu thì không có cột tổng tồn và giá nhập', async () => {
    day_du = false
    dung(<TrangTonKho />)
    expect(await screen.findByText('Paracetamol')).toBeInTheDocument()
    expect(screen.queryByText('Tổng tồn')).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: /Mở rộng|expand/i }))
    expect(await screen.findByText('L01')).toBeInTheDocument()
    expect(screen.queryByText('Giá nhập')).not.toBeInTheDocument()
  })
})

describe('TrangCanhBao', () => {
  it('hiện số mục từng nhóm', async () => {
    dung(<TrangCanhBao />)
    expect(await screen.findByText('Tồn thấp (1)')).toBeInTheDocument()
    expect(screen.getByText('Cận hạn (0)')).toBeInTheDocument()
    expect(screen.getByText('Hết hạn còn hàng (2)')).toBeInTheDocument()
  })
})
