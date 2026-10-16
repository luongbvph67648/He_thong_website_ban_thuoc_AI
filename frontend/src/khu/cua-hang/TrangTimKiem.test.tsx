import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../stores/phien'
import { loi, ok, the } from '../../test/cuaHang'
import { renderTai } from '../../test/render'

vi.setConfig({ testTimeout: 60_000 })

const GET = vi.fn()
vi.mock('../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn() },
}))

const trang = (du_lieu: unknown[], tong = du_lieu.length) => ({ du_lieu, tong, trang: 1, kich_thuoc: 12 })
const GOI_Y = [
  { kieu: 'san_pham', ten: 'Paracetamol 500mg', slug: 'paracetamol-500mg', loai_san_pham: 'thuoc_khong_ke_don', can_tu_van: false },
  { kieu: 'san_pham', ten: 'Amoxicillin 500mg', slug: 'amoxicillin-500mg', loai_san_pham: 'thuoc_ke_don', can_tu_van: true },
  { kieu: 'hoat_chat', ten: 'Paracetamol', slug: null, loai_san_pham: null, can_tu_van: false },
]

function dapUng(ghiDe: Record<string, () => unknown> = {}) {
  GET.mockImplementation(async (duong: string) => {
    if (ghiDe[duong]) return ghiDe[duong]()
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/tim-kiem') return ok(trang([the({ id: 1, ten: 'Paracetamol 500mg' }), the({ id: 2, ten: 'Amoxicillin 500mg', slug: 'amox', loai_san_pham: 'thuoc_ke_don', can_tu_van: true })]))
    if (duong === '/api/v1/tim-kiem/goi-y') return ok(GOI_Y)
    throw new Error(`Chưa giả lập ${duong}`)
  })
}
const goiTimKiem = () => GET.mock.calls.filter((c) => c[0] === '/api/v1/tim-kiem')
beforeEach(() => {
  GET.mockReset()
  localStorage.clear()
  usePhien.setState({ daKhoiPhuc: true })
})

describe('TrangTimKiem', () => {
  it('hiện kết quả; thuốc kê đơn kèm nhãn Cần tư vấn; gửi từ khóa, mã phiên và phân trang', async () => {
    dapUng()
    renderTai('/tim-kiem?q=%20para%20%20cetmol%20')
    expect(await screen.findByRole('heading', { name: /Kết quả cho “para cetmol”/ })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Paracetamol 500mg' })).toHaveAttribute('href', '/san-pham/paracetamol-500mg?nguon=tim_kiem')
    const amox = screen.getByRole('link', { name: 'Amoxicillin 500mg' })
    expect(within(amox).getByText('Cần tư vấn')).toBeInTheDocument()
    expect(screen.getByText('2 sản phẩm')).toBeInTheDocument()
    const [, tham] = goiTimKiem()[0]
    expect(tham.params.query).toEqual({ q: 'para cetmol', trang: 1, kich_thuoc: 12 })
    expect(tham.params.header['x-ma-phien']).toMatch(/^[A-Za-z0-9_-]{22}$/)
  })

  it('từ khóa trống hoặc quá ngắn không gọi API', async () => {
    dapUng()
    renderTai('/tim-kiem')
    expect(await screen.findByText(/Nhập từ khóa vào ô tìm kiếm/)).toBeInTheDocument()
    renderTai('/tim-kiem?q=p')
    expect(await screen.findByText('Hãy nhập ít nhất 2 ký tự để tìm kiếm')).toBeInTheDocument()
    expect(goiTimKiem()).toHaveLength(0)
  })

  it('không có kết quả, và lỗi tải có nút thử lại', async () => {
    dapUng({ '/api/v1/tim-kiem': () => ok(trang([])) })
    renderTai('/tim-kiem?q=zzzz')
    expect(await screen.findByText(/Không tìm thấy sản phẩm phù hợp/)).toBeInTheDocument()
    GET.mockReset()
    dapUng({ '/api/v1/tim-kiem': () => loi(500, 'LOI_HE_THONG', 'Lỗi') })
    renderTai('/tim-kiem?q=zzzz')
    expect(await screen.findByText('Không tìm kiếm được')).toBeInTheDocument()
  })

  it('phân trang giữ từ khóa trên URL', async () => {
    dapUng({ '/api/v1/tim-kiem': () => ok(trang([the()], 30)) })
    const { router } = renderTai('/tim-kiem?q=vitamin')
    await userEvent.setup().click(await screen.findByTitle('2'))
    await waitFor(() => expect(router.state.location.search).toBe('?q=vitamin&trang=2'))
    await waitFor(() => expect(goiTimKiem().at(-1)?.[1].params.query.trang).toBe(2))
  })

  it('trang vượt số trang có nút về trang 1', async () => {
    dapUng({ '/api/v1/tim-kiem': () => ok(trang([], 30)) })
    const { router } = renderTai('/tim-kiem?q=vitamin&trang=9')
    await userEvent.setup().click(await screen.findByRole('button', { name: /Về trang 1/ }))
    await waitFor(() => expect(router.state.location.search).toBe('?q=vitamin'))
  })

  it('chờ lấy lại phiên rồi mới tìm, để lịch sử tìm kiếm ghi đúng người', async () => {
    dapUng()
    usePhien.setState({ daKhoiPhuc: false })
    renderTai('/tim-kiem?q=para')
    await new Promise((r) => setTimeout(r, 150))
    expect(goiTimKiem()).toHaveLength(0)
    usePhien.setState({ daKhoiPhuc: true })
    await waitFor(() => expect(goiTimKiem()).toHaveLength(1))
  })
})

describe('OTimKiem (ô tìm kiếm ở header)', () => {
  const goiGoiY = () => GET.mock.calls.filter((c) => c[0] === '/api/v1/tim-kiem/goi-y')

  it('gõ dưới 2 ký tự không gọi gợi ý; từ 2 ký tự thì gợi ý, kèm nhãn hoạt chất và Cần tư vấn', async () => {
    dapUng()
    renderTai('/')
    const o = await screen.findByLabelText('Tìm kiếm')
    const u = userEvent.setup()
    await u.type(o, 'p')
    await new Promise((r) => setTimeout(r, 400))
    expect(goiGoiY()).toHaveLength(0)
    await u.type(o, 'ara')
    expect(await screen.findByText('Hoạt chất')).toBeInTheDocument()
    expect(goiGoiY().at(-1)?.[1].params.query).toEqual({ q: 'para' })
    expect(screen.getAllByText('Cần tư vấn').length).toBeGreaterThan(0)
  })

  it('chọn gợi ý sản phẩm mở thẳng chi tiết; chọn hoạt chất chạy tìm kiếm', async () => {
    dapUng()
    const { router } = renderTai('/')
    const o = await screen.findByLabelText('Tìm kiếm')
    const u = userEvent.setup()
    await u.type(o, 'para')
    await u.click(await screen.findByText('Amoxicillin 500mg'))
    await waitFor(() => expect(router.state.location.pathname + router.state.location.search).toBe('/san-pham/amoxicillin-500mg?nguon=tim_kiem'))
    await router.navigate('/')
    const o2 = await screen.findByLabelText('Tìm kiếm')
    await u.clear(o2)
    await u.type(o2, 'para')
    // danh sách gợi ý cũ có thể còn chạy hiệu ứng đóng (pointer-events: none): lấy phần tử cuối
    await waitFor(async () => expect((await screen.findAllByText('Hoạt chất')).length).toBeGreaterThan(0))
    await u.click((await screen.findAllByText('Hoạt chất')).at(-1)!)
    await waitFor(() => expect(router.state.location.pathname).toBe('/tim-kiem'))
    expect(router.state.location.search).toBe('?q=Paracetamol')
    // Ô giữ đúng tên đã chọn (không có hậu tố nội bộ), nên Enter tiếp theo tìm đúng từ khóa
    expect(screen.getByLabelText('Tìm kiếm')).toHaveValue('Paracetamol')
  })

  it('Enter chạy tìm kiếm đầy đủ; từ khóa 1 ký tự thì không điều hướng', async () => {
    dapUng()
    const { router } = renderTai('/')
    const o = await screen.findByLabelText('Tìm kiếm')
    const u = userEvent.setup()
    await u.type(o, 'x{Enter}')
    expect(router.state.location.pathname).toBe('/')
    await u.clear(o)
    await u.type(o, 'bo phe{Enter}')
    await waitFor(() => expect(router.state.location.pathname).toBe('/tim-kiem'))
    expect(router.state.location.search).toBe('?q=bo%20phe')
  })

  it('lỗi tải gợi ý không làm hỏng ô tìm kiếm', async () => {
    dapUng({ '/api/v1/tim-kiem/goi-y': () => loi(500, 'LOI_HE_THONG', 'Lỗi') })
    const { router } = renderTai('/')
    const o = await screen.findByLabelText('Tìm kiếm')
    await userEvent.setup().type(o, 'para{Enter}')
    await waitFor(() => expect(router.state.location.pathname).toBe('/tim-kiem'))
  })
})
