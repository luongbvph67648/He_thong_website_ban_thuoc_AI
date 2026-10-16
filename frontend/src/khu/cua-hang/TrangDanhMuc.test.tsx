import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { loi, ok, the } from '../../test/cuaHang'
import { renderTai } from '../../test/render'

vi.setConfig({ testTimeout: 60_000 })

const GET = vi.fn()
vi.mock('../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn() },
}))

const DANH_MUC = {
  id: 1,
  ten: 'Giảm đau - hạ sốt',
  slug: 'giam-dau',
  anh_url: null,
  duong_dan: [
    { ten: 'Thuốc', slug: 'thuoc' },
    { ten: 'Giảm đau - hạ sốt', slug: 'giam-dau' },
  ],
  con: [{ id: 2, ten: 'Paracetamol', slug: 'paracetamol', anh_url: null, con: [] }],
}
const BO_LOC = {
  thuong_hieu: [
    { id: 7, ten: 'Hà Thành Pharma' },
    { id: 8, ten: 'Sao Việt' },
  ],
  doi_tuong: ['Người lớn', 'Trẻ em'],
  gia_thap_nhat: '1000.00',
  gia_cao_nhat: '95000.00',
}
const trang = (du_lieu: unknown[], tong = du_lieu.length) => ({ du_lieu, tong, trang: 1, kich_thuoc: 12 })

function dapUng(ghiDe: Record<string, () => unknown> = {}) {
  GET.mockImplementation(async (duong: string) => {
    if (ghiDe[duong]) return ghiDe[duong]()
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/danh-muc/{slug}') return ok(DANH_MUC)
    if (duong === '/api/v1/bo-loc-san-pham') return ok(BO_LOC)
    if (duong === '/api/v1/san-pham') return ok(trang([the({ id: 1, ten: 'Paracetamol 500mg' }), the({ id: 2, ten: 'Ibuprofen 400mg', slug: 'ibu', con_hang: false })]))
    throw new Error(`Chưa giả lập ${duong}`)
  })
}
const queryDaGoi = () => GET.mock.calls.filter((c) => c[0] === '/api/v1/san-pham').at(-1)?.[1].params.query
beforeEach(() => {
  GET.mockReset()
})

describe('TrangDanhMuc', () => {
  it('hiện đường dẫn, danh mục con, số sản phẩm và thẻ sản phẩm; gọi API với slug trên URL', async () => {
    dapUng()
    renderTai('/danh-muc/giam-dau')
    expect(await screen.findByRole('heading', { name: 'Giảm đau - hạ sốt' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Thuốc' })).toHaveAttribute('href', '/danh-muc/thuoc')
    const con = screen.getByLabelText('Danh mục con')
    expect(within(con).getByRole('link', { name: 'Paracetamol' })).toHaveAttribute('href', '/danh-muc/paracetamol')
    expect(await screen.findByRole('link', { name: 'Paracetamol 500mg' })).toHaveAttribute('href', '/san-pham/paracetamol-500mg?nguon=danh_muc')
    expect(screen.getByText('2 sản phẩm')).toBeInTheDocument()
    expect(screen.getByText('Hết hàng')).toBeInTheDocument()
    expect(queryDaGoi()).toMatchObject({ danh_muc: 'giam-dau', sap_xep: 'moi', trang: 1, kich_thuoc: 12 })
    expect(GET).toHaveBeenCalledWith('/api/v1/danh-muc/{slug}', { params: { path: { slug: 'giam-dau' } } })
  })

  it('bộ lọc trên URL được gửi lên API; giá trị lạ bị bỏ qua', async () => {
    dapUng()
    renderTai('/danh-muc/giam-dau?loai=duoc_my_pham&thuong_hieu=7&thuong_hieu=8&gia_tu=1000&gia_den=50000&doi_tuong=Trẻ em&con_hang=1&sap_xep=gia_tang&trang=2')
    await screen.findByRole('link', { name: 'Paracetamol 500mg' })
    expect(queryDaGoi()).toEqual({
      danh_muc: 'giam-dau',
      loai: 'duoc_my_pham',
      thuong_hieu_id: [7, 8],
      gia_tu: 1000,
      gia_den: 50000,
      doi_tuong: 'Trẻ em',
      con_hang: true,
      sap_xep: 'gia_tang',
      trang: 2,
      kich_thuoc: 12,
    })
    GET.mockClear()
    renderTai('/danh-muc/giam-dau?loai=hack&sap_xep=drop&gia_tu=-1&trang=abc')
    await waitFor(() => expect(queryDaGoi()).toBeDefined())
    expect(queryDaGoi()).toMatchObject({ loai: undefined, sap_xep: 'moi', gia_tu: undefined, trang: 1 })
  })

  it('chọn thương hiệu, bật còn hàng và đổi sắp xếp cập nhật URL, đưa về trang 1', async () => {
    dapUng()
    const { router } = renderTai('/danh-muc/giam-dau?trang=3')
    await screen.findByRole('link', { name: 'Paracetamol 500mg' })
    const u = userEvent.setup()
    await u.click(await screen.findByRole('checkbox', { name: 'Sao Việt' }))
    await waitFor(() => expect(router.state.location.search).toBe('?thuong_hieu=8'))
    await u.click(screen.getByRole('switch'))
    await waitFor(() => expect(router.state.location.search).toBe('?thuong_hieu=8&con_hang=1'))
    await waitFor(() => expect(queryDaGoi()).toMatchObject({ thuong_hieu_id: [8], con_hang: true, trang: 1 }))
    expect(screen.getByRole('button', { name: /Xóa bộ lọc/ })).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: /Xóa bộ lọc/ }))
    await waitFor(() => expect(router.state.location.search).toBe(''))
  })

  it('khoảng giá chỉ áp dụng khi bấm nút', async () => {
    dapUng()
    const { router } = renderTai('/danh-muc/giam-dau')
    await screen.findByRole('link', { name: 'Paracetamol 500mg' })
    const u = userEvent.setup()
    await u.type(screen.getByLabelText('Giá từ'), '2000')
    await u.type(screen.getByLabelText('Giá đến'), '50000')
    expect(router.state.location.search).toBe('')
    await u.click(screen.getByRole('button', { name: /Áp dụng giá/ }))
    await waitFor(() => expect(router.state.location.search).toBe('?gia_tu=2000&gia_den=50000'))
    expect(screen.getByText(/Từ 1\.000/)).toBeInTheDocument() // gợi ý khoảng giá của danh mục
  })

  it('phân trang khi nhiều hơn một trang', async () => {
    dapUng({ '/api/v1/san-pham': () => ok(trang([the()], 30)) })
    const { router } = renderTai('/danh-muc/giam-dau')
    await screen.findByRole('link', { name: 'Paracetamol 500mg' })
    await userEvent.setup().click(await screen.findByTitle('2'))
    await waitFor(() => expect(router.state.location.search).toBe('?trang=2'))
    await waitFor(() => expect(queryDaGoi()).toMatchObject({ trang: 2 }))
  })

  it('danh mục không có hoặc đang ẩn là trang 404, không gọi danh sách sản phẩm', async () => {
    dapUng({ '/api/v1/danh-muc/{slug}': () => loi(404, 'KHONG_TIM_THAY', 'Không tìm thấy danh mục') })
    renderTai('/danh-muc/da-an')
    expect(await screen.findByText('Không tìm thấy danh mục')).toBeInTheDocument()
    expect(GET.mock.calls.some((c) => c[0] === '/api/v1/san-pham')).toBe(false)
  })

  it('danh sách trống, và lỗi tải danh sách có nút thử lại', async () => {
    dapUng({ '/api/v1/san-pham': () => ok(trang([])) })
    renderTai('/danh-muc/giam-dau')
    expect(await screen.findByText('Danh mục chưa có sản phẩm')).toBeInTheDocument()
    GET.mockReset()
    dapUng({ '/api/v1/san-pham': () => loi(500, 'LOI_HE_THONG', 'Lỗi') })
    renderTai('/danh-muc/giam-dau')
    expect(await screen.findByText('Không tải được danh sách sản phẩm')).toBeInTheDocument()
  })

  it('không có kết quả khi đang lọc nói rõ do bộ lọc', async () => {
    dapUng({ '/api/v1/san-pham': () => ok(trang([])) })
    renderTai('/danh-muc/giam-dau?con_hang=1')
    expect(await screen.findByText('Không có sản phẩm phù hợp bộ lọc')).toBeInTheDocument()
  })
})
