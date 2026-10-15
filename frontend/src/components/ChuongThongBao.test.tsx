import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChuongThongBao } from './ChuongThongBao'

const GET = vi.fn()
const POST = vi.fn()
vi.mock('../api/client', () => ({
  api: { GET: (...tham_so: unknown[]) => GET(...tham_so), POST: (...tham_so: unknown[]) => POST(...tham_so) },
}))

const tb = (id: number, tuyChinh: Record<string, unknown> = {}) => ({
  id,
  loai: 'don_hang',
  tieu_de: `Thông báo ${id}`,
  noi_dung: `Nội dung ${id}`,
  lien_ket: `/nhan-vien/don-hang/${id}`,
  da_doc: false,
  created_at: '2026-10-15T03:00:00Z',
  ...tuyChinh,
})

let chuaDoc = 2
let danhSach = [tb(1), tb(2), tb(3, { da_doc: true, lien_ket: null })]

function VitriHienTai() {
  return <span data-testid="vitri">{useLocation().pathname}</span>
}

function dung() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ChuongThongBao />
          <VitriHienTai />
        </MemoryRouter>
      </QueryClientProvider>
    </ConfigProvider>,
  )
}

beforeEach(() => {
  chuaDoc = 2
  danhSach = [tb(1), tb(2), tb(3, { da_doc: true, lien_ket: null })]
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string) =>
    duong.endsWith('/so-chua-doc')
      ? { data: { so_chua_doc: chuaDoc } }
      : { data: { du_lieu: danhSach, tong: danhSach.length, trang: 1, kich_thuoc: 10 } },
  )
  POST.mockImplementation(async (duong: string) => {
    if (duong.endsWith('/da-doc-tat-ca')) {
      danhSach = danhSach.map((t) => ({ ...t, da_doc: true }))
      chuaDoc = 0
    } else {
      chuaDoc -= 1
    }
    return { data: {} }
  })
})

describe('ChuongThongBao', () => {
  it('hiện số chưa đọc trên chuông và nói rõ cho trình đọc màn hình', async () => {
    dung()
    expect(await screen.findByRole('button', { name: 'Thông báo, 2 chưa đọc' })).toBeInTheDocument()
    expect(GET).toHaveBeenCalledWith('/api/v1/noi-bo/thong-bao/so-chua-doc')
  })

  it('không có thông báo chưa đọc thì không hiện số', async () => {
    chuaDoc = 0
    dung()
    expect(await screen.findByRole('button', { name: 'Thông báo' })).toBeInTheDocument()
  })

  it('chỉ tải danh sách khi mở chuông, lấy 10 thông báo mới nhất', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByRole('button', { name: /Thông báo/ })
    expect(GET).not.toHaveBeenCalledWith('/api/v1/noi-bo/thong-bao', expect.anything())
    await nguoi.click(screen.getByRole('button', { name: /Thông báo/ }))
    expect(await screen.findByText('Thông báo 1')).toBeInTheDocument()
    expect(screen.getByText('Nội dung 2')).toBeInTheDocument()
    expect(GET).toHaveBeenCalledWith('/api/v1/noi-bo/thong-bao', { params: { query: { kich_thuoc: 10 } } })
  })

  it('bấm một thông báo chưa đọc: đánh dấu đã đọc rồi chuyển tới liên kết nội bộ', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: /Thông báo/ }))
    await nguoi.click(await screen.findByText('Thông báo 2'))
    await waitFor(() => expect(screen.getByTestId('vitri')).toHaveTextContent('/nhan-vien/don-hang/2'))
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/thong-bao/{thong_bao_id}/da-doc', { params: { path: { thong_bao_id: 2 } } })
  })

  it('thông báo đã đọc không gọi đánh dấu lại; không có liên kết thì ở nguyên trang', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: /Thông báo/ }))
    await nguoi.click(await screen.findByText('Thông báo 3'))
    expect(POST).not.toHaveBeenCalled()
    expect(screen.getByTestId('vitri')).toHaveTextContent('/')
  })

  it.each(['https://trang-lua-dao.example/x', '//trang-lua-dao.example', 'javascript:alert(1)', '/\\trang-lua-dao.example'])(
    'liên kết ngoài ứng dụng (%s) không bao giờ được điều hướng tới',
    async (lienKet) => {
      danhSach = [tb(7, { lien_ket: lienKet })]
      const nguoi = userEvent.setup()
      dung()
      await nguoi.click(await screen.findByRole('button', { name: /Thông báo/ }))
      await nguoi.click(await screen.findByText('Thông báo 7'))
      expect(screen.getByTestId('vitri')).toHaveTextContent('/')
    },
  )

  it('đánh dấu tất cả đã đọc rồi tải lại số đếm', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: 'Thông báo, 2 chưa đọc' }))
    await nguoi.click(await screen.findByRole('button', { name: 'Đánh dấu tất cả đã đọc' }))
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/thong-bao/da-doc-tat-ca')
    expect(await screen.findByRole('button', { name: 'Thông báo' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Đánh dấu tất cả đã đọc' })).toBeDisabled()
  })

  it('chưa có thông báo nào thì báo rõ', async () => {
    danhSach = []
    chuaDoc = 0
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: /Thông báo/ }))
    expect(await screen.findByText('Chưa có thông báo')).toBeInTheDocument()
  })

  it('tải danh sách lỗi thì báo thay vì treo', async () => {
    GET.mockImplementation(async (duong: string) =>
      duong.endsWith('/so-chua-doc') ? { data: { so_chua_doc: 1 } } : { error: { ma_loi: 'LOI_HE_THONG', thong_diep: 'x', chi_tiet: null } },
    )
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(await screen.findByRole('button', { name: /Thông báo/ }))
    expect(await screen.findByText(/Không tải được thông báo/)).toBeInTheDocument()
  })
})
