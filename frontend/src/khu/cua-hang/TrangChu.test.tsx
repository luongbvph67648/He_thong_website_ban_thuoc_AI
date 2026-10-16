import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { chiTiet, loi, ok, the } from '../../test/cuaHang'
import { renderTai } from '../../test/render'

vi.setConfig({ testTimeout: 60_000 })

const GET = vi.fn()
vi.mock('../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn() },
}))

const CAY = [
  { id: 1, ten: 'Thuốc', slug: 'thuoc', anh_url: null, con: [{ id: 2, ten: 'Giảm đau', slug: 'giam-dau', anh_url: null, con: [] }] },
  { id: 3, ten: 'Dược mỹ phẩm', slug: 'duoc-my-pham', anh_url: null, con: [] },
]
const BANNER = (o: object) => ({ id: 1, tieu_de: 'Khuyến mãi', anh_url: '/banner/chinh-1.svg', lien_ket: '/danh-muc/thuoc', vi_tri: 'trang_chu_chinh', ...o })
const TRANG_CHU = (o: object = {}) => ({ banner_chinh: [], banner_phu: [], noi_bat: [], ban_chay: [], ...o })

function dapUng(trangChu: unknown) {
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/danh-muc') return ok(CAY)
    if (duong === '/api/v1/trang-chu') return typeof trangChu === 'function' ? trangChu() : ok(trangChu)
    throw new Error(`Chưa giả lập ${duong}`)
  })
}
beforeEach(() => {
  GET.mockReset()
})

describe('TrangChu', () => {
  it('hiện banner (liên kết nội bộ), danh mục gốc, nổi bật và bán chạy', async () => {
    dapUng(
      TRANG_CHU({
        banner_chinh: [BANNER({})],
        banner_phu: [BANNER({ id: 2, tieu_de: 'Banner phụ', anh_url: '/banner/phu-1.svg', lien_ket: 'https://example.com/km', vi_tri: 'trang_chu_phu' })],
        noi_bat: [the({ id: 1, ten: 'Sản phẩm nổi bật A' })],
        ban_chay: [the({ id: 2, ten: 'Sản phẩm bán chạy B', slug: 'b' })],
      }),
    )
    renderTai('/')
    const noiBat = await screen.findByRole('region', { name: 'Sản phẩm nổi bật' })
    expect(within(noiBat).getByRole('link', { name: 'Sản phẩm nổi bật A' })).toHaveAttribute('href', '/san-pham/paracetamol-500mg?nguon=trang_chu')
    const banChay = screen.getByRole('region', { name: 'Bán chạy' })
    expect(within(banChay).getByRole('link', { name: 'Sản phẩm bán chạy B' })).toHaveAttribute('href', '/san-pham/b?nguon=trang_chu')

    const chinh = screen.getByRole('region', { name: 'Banner chính' })
    for (const a of within(chinh).getAllByAltText('Khuyến mãi')) expect(a.closest('a')).toHaveAttribute('href', '/danh-muc/thuoc')
    const phu = screen.getByRole('region', { name: 'Banner phụ' })
    const lienKetNgoai = within(phu).getByAltText('Banner phụ').closest('a') as HTMLAnchorElement
    expect(lienKetNgoai).toHaveAttribute('href', 'https://example.com/km')
    expect(lienKetNgoai).toHaveAttribute('rel', 'noopener noreferrer')
    expect(lienKetNgoai).toHaveAttribute('target', '_blank')

    const danhMuc = screen.getByRole('region', { name: 'Danh mục' })
    expect(within(danhMuc).getByRole('link', { name: 'Dược mỹ phẩm' })).toHaveAttribute('href', '/danh-muc/duoc-my-pham')
    expect(within(danhMuc).queryByText('Giảm đau')).not.toBeInTheDocument() // chỉ danh mục gốc
  })

  it('liên kết banner nguy hiểm không thành href; ảnh không hợp lệ bị bỏ', async () => {
    dapUng(
      TRANG_CHU({
        banner_chinh: [
          BANNER({ id: 1, tieu_de: 'Độc hại', lien_ket: 'javascript:alert(1)' }),
          BANNER({ id: 2, tieu_de: 'Ảnh lạ', anh_url: 'javascript:alert(2)' }),
          BANNER({ id: 3, tieu_de: 'Giao thức tương đối', lien_ket: '//evil.example' }),
        ],
      }),
    )
    renderTai('/')
    const chinh = await screen.findByRole('region', { name: 'Banner chính' })
    for (const ten of ['Độc hại', 'Giao thức tương đối']) {
      // Carousel nhân bản slide để lặp vòng: kiểm tra mọi bản sao
      const anh = within(chinh).getAllByAltText(ten)
      expect(anh.length).toBeGreaterThan(0)
      for (const a of anh) expect(a.closest('a')).toBeNull() // hiện ảnh nhưng không có liên kết
    }
    expect(within(chinh).queryByAltText('Ảnh lạ')).not.toBeInTheDocument()
    expect(chinh.querySelector('a[href^="javascript"]')).toBeNull()
  })

  it('khu trống thì ẩn cả khu; toàn bộ trống hiện thông báo', async () => {
    dapUng(TRANG_CHU({ noi_bat: [the()] }))
    renderTai('/')
    await screen.findByRole('region', { name: 'Sản phẩm nổi bật' })
    expect(screen.queryByRole('region', { name: 'Bán chạy' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Banner chính' })).not.toBeInTheDocument()
  })

  it('lỗi tải hiện cảnh báo có nút thử lại', async () => {
    dapUng(() => loi(500, 'LOI_HE_THONG', 'Lỗi'))
    renderTai('/')
    expect(await screen.findByText('Không tải được trang chủ')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Thử lại/ })).toBeInTheDocument()
  })

  it('thanh danh mục 3 cấp ở layout, tên là liên kết tới trang danh mục', async () => {
    dapUng(TRANG_CHU())
    renderTai('/')
    const thanh = await screen.findByRole('navigation', { name: 'Danh mục sản phẩm' })
    expect(await within(thanh).findByRole('link', { name: 'Dược mỹ phẩm' })).toHaveAttribute('href', '/danh-muc/duoc-my-pham')
    expect(chiTiet().ten).toBe('Paracetamol 500mg')
  })
})
