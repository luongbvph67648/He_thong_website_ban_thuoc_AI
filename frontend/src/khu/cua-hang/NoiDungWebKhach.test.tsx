import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { loi, ok } from '../../test/cuaHang'
import { renderTai } from '../../test/render'

vi.setConfig({ testTimeout: 60_000 })

const GET = vi.fn()
vi.mock('../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn() },
}))

const trang = (du_lieu: unknown[], tong = du_lieu.length) => ({ du_lieu, tong, trang: 1, kich_thuoc: 9 })
const tomTat = (o: object = {}) => ({
  id: 1,
  tieu_de: 'Phòng cảm cúm',
  slug: 'phong-cam-cum',
  loai: 'bai_viet',
  anh_bia_url: null,
  tom_tat: 'Rửa tay thường xuyên.',
  ngay_dang: '2026-10-10T03:00:00Z',
  noi_dung: null,
  ...o,
})
const chiTiet = (o: object = {}) => ({
  id: 1,
  tieu_de: 'Phòng cảm cúm',
  slug: 'phong-cam-cum',
  loai: 'bai_viet',
  anh_bia_url: null,
  noi_dung: '## Rửa tay\n\nRửa tay **thường xuyên**.',
  ngay_dang: '2026-10-10T03:00:00Z',
  ...o,
})

function dapUng(ghiDe: Record<string, (tham: { params: { query?: Record<string, unknown> } }) => unknown> = {}) {
  GET.mockImplementation(async (duong: string, tham: { params: { query?: Record<string, unknown> } }) => {
    if (ghiDe[duong]) return ghiDe[duong](tham)
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/bai-viet') {
      return ok(trang(tham?.params?.query?.loai === 'chinh_sach' ? [tomTat({ id: 5, tieu_de: 'Chính sách đổi trả', slug: 'doi-tra', loai: 'chinh_sach' })] : []))
    }
    throw new Error(`Chưa giả lập ${duong}`)
  })
}
beforeEach(() => {
  GET.mockReset()
})

describe('chân trang', () => {
  it('liệt kê bài viết, hỏi đáp và các trang chính sách đã đăng', async () => {
    dapUng()
    renderTai('/')
    const chan = (await screen.findByText(/không thay thế tư vấn của dược sĩ/)).closest('footer') as HTMLElement
    expect(within(chan).getByRole('link', { name: 'Bài viết' })).toHaveAttribute('href', '/bai-viet')
    expect(within(chan).getByRole('link', { name: 'Hỏi đáp' })).toHaveAttribute('href', '/hoi-dap')
    expect(await within(chan).findByRole('link', { name: 'Chính sách đổi trả' })).toHaveAttribute('href', '/chinh-sach/doi-tra')
  })

  it('lỗi tải chính sách chỉ ẩn phần chính sách', async () => {
    dapUng({ '/api/v1/bai-viet': () => loi(500, 'LOI_HE_THONG', 'Lỗi') })
    renderTai('/')
    const chan = (await screen.findByText(/không thay thế tư vấn của dược sĩ/)).closest('footer') as HTMLElement
    expect(within(chan).getByRole('link', { name: 'Hỏi đáp' })).toBeInTheDocument()
  })
})

describe('TrangDanhSachBaiViet', () => {
  it('hiện thẻ bài, tìm theo từ khóa trên URL và gọi đúng tham số', async () => {
    dapUng({ '/api/v1/bai-viet': () => ok(trang([tomTat(), tomTat({ id: 2, tieu_de: 'Chăm sóc da', slug: 'cham-soc-da', anh_bia_url: '/api/v1/tep/bai-viet/a.jpg' })], 2)) })
    const { router } = renderTai('/bai-viet?q=%20da%20&trang=2')
    // Chân trang cũng gọi cùng route (mock trả chung), nên chỉ xét thẻ trong nội dung chính
    const noiDung = (await screen.findByRole('heading', { name: 'Bài viết sức khỏe', level: 2 })).closest('main') as HTMLElement
    expect(await within(noiDung).findByRole('link', { name: 'Phòng cảm cúm' })).toHaveAttribute('href', '/bai-viet/phong-cam-cum')
    expect(within(noiDung).getByRole('link', { name: 'Chăm sóc da' })).toBeInTheDocument()
    const goi = GET.mock.calls.filter((c) => c[0] === '/api/v1/bai-viet' && c[1].params.query.loai === 'bai_viet').at(-1)
    expect(goi?.[1].params.query).toEqual({ loai: 'bai_viet', q: 'da', trang: 2, kich_thuoc: 9 })
    await userEvent.setup().type(screen.getByLabelText('Tìm bài viết'), '{Enter}')
    expect(router.state.location.pathname).toBe('/bai-viet')
  })

  it('rỗng, không có kết quả tìm, trang vượt số trang, lỗi tải', async () => {
    dapUng({ '/api/v1/bai-viet': () => ok(trang([])) })
    renderTai('/bai-viet')
    expect(await screen.findByText('Chưa có bài viết')).toBeInTheDocument()
    GET.mockReset()
    dapUng({ '/api/v1/bai-viet': () => ok(trang([])) })
    renderTai('/bai-viet?q=xyz')
    expect(await screen.findByText('Không có bài viết phù hợp')).toBeInTheDocument()
    GET.mockReset()
    dapUng({ '/api/v1/bai-viet': () => ok(trang([], 30)) })
    renderTai('/bai-viet?trang=9')
    expect(await screen.findByText('Trang này không có bài viết')).toBeInTheDocument()
    GET.mockReset()
    dapUng({ '/api/v1/bai-viet': () => loi(500, 'LOI_HE_THONG', 'Lỗi') })
    renderTai('/bai-viet')
    expect(await screen.findByText('Không tải được bài viết')).toBeInTheDocument()
  })
})

describe('TrangBaiViet', () => {
  it('đọc bài: tiêu đề, Markdown đã render, lưu ý tham khảo', async () => {
    dapUng({ '/api/v1/bai-viet/{slug}': () => ok(chiTiet()) })
    renderTai('/bai-viet/phong-cam-cum')
    expect(await screen.findByRole('heading', { name: 'Phòng cảm cúm', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Rửa tay', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('thường xuyên').tagName).toBe('STRONG')
    expect(screen.getByText(/không thay thế tư vấn của bác sĩ hoặc dược sĩ/)).toBeInTheDocument()
  })

  it('nội dung độc hại hiện thành chữ, không thành phần tử', async () => {
    dapUng({ '/api/v1/bai-viet/{slug}': () => ok(chiTiet({ noi_dung: '<script>window.hack=1</script>\n\n[bấm](javascript:alert(1))', anh_bia_url: 'javascript:alert(1)' })) })
    const { container } = renderTai('/bai-viet/phong-cam-cum')
    await screen.findByRole('heading', { name: 'Phòng cảm cúm', level: 1 })
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('a[href^="javascript"]')).toBeNull()
    expect(container.querySelector('img[src^="javascript"]')).toBeNull()
  })

  it('trang chính sách dùng đúng loại; slug của loại khác là 404', async () => {
    dapUng({ '/api/v1/bai-viet/{slug}': () => ok(chiTiet({ tieu_de: 'Chính sách đổi trả', slug: 'doi-tra', loai: 'chinh_sach' })) })
    renderTai('/chinh-sach/doi-tra')
    expect(await screen.findByRole('heading', { name: 'Chính sách đổi trả', level: 1 })).toBeInTheDocument()
    expect(screen.queryByText(/không thay thế tư vấn của bác sĩ hoặc dược sĩ\./)).not.toBeInTheDocument() // lưu ý chỉ cho bài sức khỏe
    GET.mockReset()
    dapUng({ '/api/v1/bai-viet/{slug}': () => ok(chiTiet({ loai: 'chinh_sach' })) })
    renderTai('/bai-viet/doi-tra')
    expect(await screen.findByText('Không tìm thấy trang')).toBeInTheDocument() // chính sách không đọc ở /bai-viet
  })

  it('không có / chưa duyệt / slug sai mẫu đều là 404; lỗi máy chủ có nút thử lại', async () => {
    dapUng({ '/api/v1/bai-viet/{slug}': () => loi(404, 'KHONG_TIM_THAY', 'Không tìm thấy bài viết') })
    renderTai('/bai-viet/khong-co')
    expect(await screen.findByText('Không tìm thấy trang')).toBeInTheDocument()
    GET.mockReset()
    dapUng({ '/api/v1/bai-viet/{slug}': () => loi(400, 'DU_LIEU_KHONG_HOP_LE', 'Dữ liệu không hợp lệ') })
    renderTai('/bai-viet/Sai_Mau')
    expect(await screen.findByText('Không tìm thấy trang')).toBeInTheDocument()
    GET.mockReset()
    dapUng({ '/api/v1/bai-viet/{slug}': () => loi(500, 'LOI_HE_THONG', 'Lỗi') })
    renderTai('/bai-viet/x')
    expect(await screen.findByText('Không tải được trang')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Thử lại/ })).toBeInTheDocument()
  })
})

describe('TrangHoiDap', () => {
  it('mỗi câu hỏi là một mục gập, câu trả lời render Markdown; gọi với kem_noi_dung', async () => {
    dapUng({
      '/api/v1/bai-viet': () =>
        ok(trang([tomTat({ id: 1, tieu_de: 'Giao hàng mất bao lâu?', loai: 'faq', noi_dung: 'Từ **1 đến 3** ngày.' }), tomTat({ id: 2, tieu_de: 'Có đổi trả không?', loai: 'faq', noi_dung: 'Có, trong 7 ngày.' })])),
    })
    renderTai('/hoi-dap')
    expect(await screen.findByRole('heading', { name: 'Hỏi đáp thường gặp', level: 1 })).toBeInTheDocument()
    await userEvent.setup().click(await screen.findByText('Giao hàng mất bao lâu?'))
    expect(await screen.findByText('1 đến 3')).toBeInTheDocument()
    const goi = GET.mock.calls.filter((c) => c[0] === '/api/v1/bai-viet' && c[1].params.query.loai === 'faq').at(-1)
    expect(goi?.[1].params.query).toEqual({ loai: 'faq', kem_noi_dung: true, kich_thuoc: 50 })
  })

  it('rỗng và lỗi tải', async () => {
    dapUng({ '/api/v1/bai-viet': () => ok(trang([])) })
    renderTai('/hoi-dap')
    expect(await screen.findByText('Chưa có câu hỏi nào')).toBeInTheDocument()
    GET.mockReset()
    dapUng({ '/api/v1/bai-viet': () => loi(500, 'LOI_HE_THONG', 'Lỗi') })
    renderTai('/hoi-dap')
    await waitFor(() => expect(screen.getByText('Không tải được câu hỏi')).toBeInTheDocument())
  })
})
