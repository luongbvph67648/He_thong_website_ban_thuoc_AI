import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangSanPham from './TrangSanPham'

vi.setConfig({ testTimeout: 60_000 }) // antd + jsdom chậm; CI chỉ có 2 vCPU mà chạy song song nhiều file

const GET = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a) } }))

const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const SAN_PHAM = [
  {
    id: 11,
    sku: 'PARA500',
    ten: 'Paracetamol 500mg',
    slug: 'paracetamol-500mg',
    loai_san_pham: 'thuoc_khong_ke_don',
    danh_muc_id: 3,
    ten_danh_muc: 'Giảm đau',
    thuong_hieu_id: 1,
    ten_thuong_hieu: 'Hậu Giang',
    trang_thai: 'dang_kinh_doanh',
    la_noi_bat: true,
    don_vi_co_so: 'Viên',
    gia_mac_dinh: '90000.00',
    anh_chinh_url: '/api/v1/tep/san-pham/a.jpg',
    created_at: '2026-10-01T03:00:00Z',
  },
  {
    id: 12,
    sku: 'AMOX',
    ten: 'Amoxicillin 500mg',
    slug: 'amoxicillin-500mg',
    loai_san_pham: 'thuoc_ke_don',
    danh_muc_id: 3,
    ten_danh_muc: 'Kháng sinh',
    thuong_hieu_id: null,
    ten_thuong_hieu: null,
    trang_thai: 'ngung_kinh_doanh',
    la_noi_bat: false,
    don_vi_co_so: 'Viên',
    gia_mac_dinh: null,
    anh_chinh_url: null,
    created_at: '2026-10-02T03:00:00Z',
  },
]

function dung(duong = '/quan-tri/san-pham', quyen: 'day_du' | 'chi_xem' = 'day_du') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'product.commercial.manage': quyen } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <Routes>
              <Route path="/quan-tri/san-pham" element={<TrangSanPham />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

const thamSoDaGoi = () => {
  const goi = GET.mock.calls.filter((c) => c[0] === '/api/v1/noi-bo/san-pham').at(-1)
  return goi?.[1].params.query
}

beforeEach(() => {
  GET.mockReset()
  GET.mockImplementation(async (duong: string) =>
    duong === '/api/v1/noi-bo/danh-muc' ? ok([]) : ok({ du_lieu: SAN_PHAM, tong: 2, trang: 1, kich_thuoc: 20 }),
  )
})

describe('TrangSanPham', () => {
  it('hiện từng sản phẩm: tên là liên kết giữ tiền tố khu, giá mặc định, nhãn nổi bật, loại và trạng thái', async () => {
    dung()
    const lienKet = await screen.findByRole('link', { name: 'Paracetamol 500mg' })
    expect(lienKet).toHaveAttribute('href', '/quan-tri/san-pham/11')
    const hang = lienKet.closest('tr') as HTMLElement
    expect(within(hang).getByText('PARA500')).toBeInTheDocument()
    expect(within(hang).getByText('Nổi bật')).toBeInTheDocument()
    expect(within(hang).getByText('Thuốc không kê đơn')).toBeInTheDocument()
    expect(within(hang).getByText('Giảm đau')).toBeInTheDocument()
    expect(within(hang).getByText('Hậu Giang')).toBeInTheDocument()
    expect(within(hang).getByText(/90\.000/)).toBeInTheDocument()
    expect(within(hang).getByAltText('Ảnh Paracetamol 500mg')).toHaveAttribute('src', '/api/v1/tep/san-pham/a.jpg')

    const hang2 = (await screen.findByText('Amoxicillin 500mg')).closest('tr') as HTMLElement
    expect(within(hang2).getByText('Thuốc kê đơn')).toBeInTheDocument()
    expect(within(hang2).getByText('Ngừng kinh doanh')).toBeInTheDocument()
    expect(within(hang2.parentElement as HTMLElement).getAllByText('—').length).toBeGreaterThanOrEqual(2) // thương hiệu và giá trống
  })

  it('bộ lọc trên URL được gửi lên máy chủ; giá trị lạ bị bỏ qua', async () => {
    dung('/quan-tri/san-pham?q=para&loai=thuoc_ke_don&trang_thai=ngung_kinh_doanh&danh_muc_id=3&sap_xep=-ten&trang=2')
    await screen.findByText('Paracetamol 500mg')
    expect(thamSoDaGoi()).toEqual({ q: 'para', loai: 'thuoc_ke_don', trang_thai: 'ngung_kinh_doanh', danh_muc_id: 3, sap_xep: '-ten', trang: 2, kich_thuoc: 20 })
  })

  it('tham số hỏng trên URL không đi tới máy chủ', async () => {
    dung('/quan-tri/san-pham?loai=hack&trang_thai=x&danh_muc_id=abc&sap_xep=mat_khau&trang=-5')
    await screen.findByText('Paracetamol 500mg')
    expect(thamSoDaGoi()).toEqual({ q: undefined, loai: undefined, trang_thai: undefined, danh_muc_id: undefined, sap_xep: undefined, trang: 1, kich_thuoc: 20 })
  })

  it('nút Thêm sản phẩm trỏ tới trang tạo trong khu quản trị, chỉ hiện với quyền đầy đủ', async () => {
    const { unmount } = dung()
    expect(await screen.findByRole('link', { name: /Thêm sản phẩm/ })).toHaveAttribute('href', '/quan-tri/san-pham/moi')
    unmount()
    dung('/quan-tri/san-pham', 'chi_xem')
    await screen.findByText('Paracetamol 500mg')
    expect(screen.queryByRole('link', { name: /Thêm sản phẩm/ })).not.toBeInTheDocument()
  })

  it('danh sách rỗng và lỗi tải', async () => {
    GET.mockImplementation(async (duong: string) => (duong === '/api/v1/noi-bo/danh-muc' ? ok([]) : ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 20 })))
    const { unmount } = dung()
    expect(await screen.findByText('Không có sản phẩm phù hợp')).toBeInTheDocument()
    unmount()
    GET.mockImplementation(async (duong: string) =>
      duong === '/api/v1/noi-bo/danh-muc' ? ok([]) : { error: { ma_loi: 'LOI_HE_THONG', thong_diep: 'x', chi_tiet: null }, response: { ok: false, status: 500 } },
    )
    dung()
    expect(await screen.findByText('Không tải được danh sách sản phẩm')).toBeInTheDocument()
  })
})
