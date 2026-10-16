import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangNoiDungChuyenMon from './TrangNoiDungChuyenMon'

vi.setConfig({ testTimeout: 60_000 }) // antd + jsdom chậm; CI chỉ có 2 vCPU mà chạy song song nhiều file

const GET = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a) } }))

const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const DONG = [
  { san_pham_id: 11, sku: 'PARA500', ten: 'Paracetamol 500mg', loai_san_pham: 'thuoc_khong_ke_don', phien_ban_da_duyet: 2, ngay_duyet: '2026-10-10T03:00:00Z', phien_ban_nhap_moi_nhat: 3, cho_duyet: true },
  { san_pham_id: 12, sku: 'AMOX', ten: 'Amoxicillin 500mg', loai_san_pham: 'thuoc_ke_don', phien_ban_da_duyet: null, ngay_duyet: null, phien_ban_nhap_moi_nhat: null, cho_duyet: false },
]

function dung(duong = '/nhan-vien/noi-dung-chuyen-mon') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'DS', vaiTro: 'PHARMACIST' }, quyen: { 'content.professional.edit': 'day_du' } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <Routes>
              <Route path="/nhan-vien/noi-dung-chuyen-mon" element={<TrangNoiDungChuyenMon />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}
const thamSoDaGoi = () => GET.mock.calls.filter((c) => c[0] === '/api/v1/noi-bo/chuyen-mon').at(-1)?.[1].params.query

beforeEach(() => {
  GET.mockReset()
  GET.mockImplementation(async () => ok({ du_lieu: DONG, tong: 2, trang: 1, kich_thuoc: 20 }))
})

describe('TrangNoiDungChuyenMon', () => {
  it('hiện tình trạng từng sản phẩm; tên là liên kết giữ tiền tố khu nhân viên', async () => {
    dung()
    const lienKet = await screen.findByRole('link', { name: 'Paracetamol 500mg' })
    expect(lienKet).toHaveAttribute('href', '/nhan-vien/noi-dung-chuyen-mon/11')
    const hang = lienKet.closest('tr') as HTMLElement
    expect(within(hang).getByText(/Bản 2/)).toBeInTheDocument()
    expect(within(hang).getByText('Bản nháp 3')).toBeInTheDocument()
    const hang2 = (await screen.findByText('Amoxicillin 500mg')).closest('tr') as HTMLElement
    expect(within(hang2).getByText('Chưa có')).toBeInTheDocument()
    expect(within(hang2).getByText('Thuốc kê đơn')).toBeInTheDocument()
    expect(within(hang2).queryByText(/Bản nháp/)).not.toBeInTheDocument()
  })

  it('bộ lọc trên URL được gửi lên máy chủ; giá trị lạ bị bỏ qua', async () => {
    dung('/nhan-vien/noi-dung-chuyen-mon?q=para&loc=cho_duyet&trang=2')
    await screen.findByText('Paracetamol 500mg')
    expect(thamSoDaGoi()).toEqual({ q: 'para', loc: 'cho_duyet', trang: 2, kich_thuoc: 20 })
    GET.mockClear()
    dung('/nhan-vien/noi-dung-chuyen-mon?loc=hack&trang=-3')
    await screen.findAllByText('Paracetamol 500mg')
    expect(thamSoDaGoi()).toEqual({ q: undefined, loc: undefined, trang: 1, kich_thuoc: 20 })
  })

  it('rỗng và lỗi tải', async () => {
    GET.mockImplementation(async () => ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 20 }))
    const { unmount } = dung()
    expect(await screen.findByText('Không có sản phẩm phù hợp')).toBeInTheDocument()
    unmount()
    GET.mockImplementation(async () => ({ error: { ma_loi: 'LOI_HE_THONG', thong_diep: 'x', chi_tiet: null }, response: { ok: false, status: 500 } }))
    dung()
    expect(await screen.findByText('Không tải được danh sách sản phẩm')).toBeInTheDocument()
  })
})
