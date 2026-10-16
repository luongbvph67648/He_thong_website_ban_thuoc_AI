import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangBaiVietChoDuyet from './TrangBaiVietChoDuyet'

vi.setConfig({ testTimeout: 90_000 })

const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a) } }))

const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string) => ({ error: { ma_loi, thong_diep, chi_tiet: null }, response: { ok: false, status } })
const TOM_TAT = { id: 7, tieu_de: 'Phòng cảm cúm', slug: 'phong-cam-cum', loai: 'bai_viet', trang_thai: 'nhap', tac_gia: 'Admin Một', created_at: '2026-10-10T03:00:00Z', updated_at: null }
const CHI_TIET = { ...TOM_TAT, noi_dung: '## Rửa tay\n\nRửa tay **thường xuyên**.\n\n<script>window.hack=1</script>', anh_bia_url: null, dua_vao_ai: true, duoc_si_duyet: null, ngay_duyet: null, phien_ban: 'aaaaaaaaaaaaaaaa' }

function dung(quyen: Record<string, 'day_du' | 'chi_xem'> = { 'content.approve': 'day_du' }) {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'DS', vaiTro: 'PHARMACIST' }, quyen })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter>
            <TrangBaiVietChoDuyet />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

let chiTiet: typeof CHI_TIET
beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  chiTiet = CHI_TIET
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/bai-viet-cho-duyet') return ok({ du_lieu: [TOM_TAT], tong: 1, trang: 1, kich_thuoc: 20 })
    if (duong === '/api/v1/noi-bo/bai-viet-cho-duyet/{bai_viet_id}') return ok(chiTiet)
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('TrangBaiVietChoDuyet', () => {
  it('liệt kê bài chờ duyệt; mở ra đọc toàn văn đã render, HTML thô không chạy', async () => {
    const { baseElement } = dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Phòng cảm cúm'))
    const khung = await screen.findByRole('dialog')
    expect(await within(khung).findByRole('heading', { name: 'Rửa tay', level: 2 })).toBeInTheDocument()
    expect(within(khung).getByText('Người soạn: Admin Một')).toBeInTheDocument()
    expect(within(khung).getByText(/kho tri thức AI/)).toBeInTheDocument()
    expect(baseElement.querySelector('script')).toBeNull()
  })

  it('duyệt gửi đúng phien_ban đã đọc, rồi đóng và làm mới danh sách', async () => {
    POST.mockResolvedValue(ok({ ...CHI_TIET, trang_thai: 'da_duyet' }))
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Phòng cảm cúm'))
    const khung = await screen.findByRole('dialog')
    await u.click(await within(khung).findByText('Duyệt bài'))
    await u.click((await waitFor(() => document.querySelector('.ant-popover .ant-btn-primary'))) as HTMLElement)
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/bai-viet-cho-duyet/{bai_viet_id}/duyet')
    expect(POST.mock.calls[0][1]).toEqual({ params: { path: { bai_viet_id: 7 } }, body: { phien_ban: 'aaaaaaaaaaaaaaaa' } })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('409 (Admin vừa sửa): báo, tải lại nội dung mới và lần duyệt sau gửi phien_ban mới', async () => {
    POST.mockResolvedValueOnce(loi(409, 'DU_LIEU_DA_THAY_DOI', 'Đã sửa')).mockResolvedValueOnce(ok({ ...CHI_TIET, trang_thai: 'da_duyet' }))
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Phòng cảm cúm'))
    const khung = await screen.findByRole('dialog')
    await u.click(await within(khung).findByText('Duyệt bài'))
    chiTiet = { ...CHI_TIET, noi_dung: 'Nội dung Admin vừa sửa', phien_ban: 'ffffffffffffffff' } // đổi sau khi dược sĩ mở
    await u.click((await waitFor(() => document.querySelector('.ant-popover .ant-btn-primary'))) as HTMLElement)
    expect(await within(khung).findByText(/vừa được sửa/)).toBeInTheDocument()
    expect(await within(khung).findByText('Nội dung Admin vừa sửa')).toBeInTheDocument() // buộc đọc lại bản mới
    await u.click(within(khung).getByText('Duyệt bài'))
    await u.click((await waitFor(() => document.querySelector('.ant-popover .ant-btn-primary'))) as HTMLElement)
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(2))
    expect(POST.mock.calls[1][1].body).toEqual({ phien_ban: 'ffffffffffffffff' })
  })

  it('không có bài chờ duyệt; chỉ xem không có nút duyệt', async () => {
    GET.mockImplementation(async (duong: string) =>
      duong === '/api/v1/noi-bo/bai-viet-cho-duyet' ? ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 20 }) : ok(chiTiet),
    )
    dung()
    expect(await screen.findByText('Không có bài viết nào đang chờ duyệt')).toBeInTheDocument()
  })

  it('quyền chỉ xem: đọc được nhưng không thấy nút duyệt', async () => {
    dung({ 'content.approve': 'chi_xem' })
    const u = userEvent.setup()
    await u.click(await screen.findByText('Phòng cảm cúm'))
    const khung = await screen.findByRole('dialog')
    await within(khung).findByRole('heading', { name: 'Rửa tay', level: 2 })
    expect(within(khung).queryByText('Duyệt bài')).not.toBeInTheDocument()
  })
})
