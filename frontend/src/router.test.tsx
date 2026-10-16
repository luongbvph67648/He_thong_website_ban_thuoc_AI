import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { matchRoutes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from './stores/phien'
import { TRANG_CUA_HANG } from './khu/cua-hang/trang'
import { MUC_NHAN_VIEN } from './khu/nhan-vien/menu'
import { MUC_QUAN_TRI } from './khu/quan-tri/menu'
import { taoRoutes } from './router'
import { renderTai } from './test/render'

// Khung nội bộ có chuông thông báo gọi API: thay client bằng bản giả để test không đụng tới mạng.
const { GET, POST, GET_MAC_DINH } = vi.hoisted(() => {
  // Mặc định máy chủ "không trả hồ sơ" để không ghi đè phiên giả của từng test; test riêng thay bằng mockImplementation.
  const macDinh = async (duong: string): Promise<{ data?: unknown; error?: unknown }> => {
    if (duong.endsWith('/so-chua-doc')) return { data: { so_chua_doc: 0 } }
    if (duong.endsWith('/noi-bo/toi')) return { error: { ma_loi: 'LOI_HE_THONG', thong_diep: 'x', chi_tiet: null } }
    if (duong === '/api/v1/trang-chu') return { data: { banner_chinh: [], banner_phu: [], noi_bat: [], ban_chay: [] } }
    if (duong === '/api/v1/danh-muc') return { data: [] }
    return { data: { du_lieu: [], tong: 0, trang: 1, kich_thuoc: 10 } }
  }
  return {
    GET_MAC_DINH: macDinh,
    GET: vi.fn(macDinh),
    POST: vi.fn(async (_duong: string) => ({ response: { status: 204 } })),
  }
})
vi.mock('./api/client', () => ({ api: { GET, POST } }))

const GOC_REPO = resolve(__dirname, '../..')
const doc = (duong: string) => readFileSync(resolve(GOC_REPO, duong), 'utf-8')

/** Đọc bảng ở spec 09 mục 2.2/2.3: mỗi dòng cho danh sách đường dẫn và mã quyền (trong dấu `). */
function docBangSpec(tieuDe: string, soCot: number) {
  const phan = doc('docs/spec/09-frontend.md').split(tieuDe)[1].split(/\n### |\n## /)[0]
  const dong: { duong: string[]; quyen: string[] }[] = []
  for (const d of phan.split('\n')) {
    const o = d.split('|').slice(1, -1).map((c) => c.trim())
    if (o.length !== soCot || !o[0].startsWith('`')) continue
    const lay = (c: string) => [...c.matchAll(/`([^`]+)`/g)].map((m) => m[1])
    dong.push({ duong: lay(o[0]), quyen: lay(o[soCot - 1]) })
  }
  return dong
}

/** Ghép đường dẫn với quyền như spec: số bằng nhau thì theo vị trí, một quyền thì dùng chung, nhiều quyền cho một trang thì "một trong". */
function ghepTheoSpec(dong: { duong: string[]; quyen: string[] }[]) {
  const ket = new Map<string, string[]>()
  for (const { duong, quyen } of dong) {
    duong.forEach((d, i) => ket.set(d, duong.length === quyen.length ? [quyen[i]] : quyen))
  }
  return ket
}

const congCu = (muc: readonly { duong: string; quyen: readonly string[] }[]) =>
  new Map(muc.map((m) => [m.duong, [...m.quyen]]))

describe('bảng đường dẫn khớp spec 09', () => {
  it('khu nhân viên: đủ trang, đúng mã quyền (mục 2.2)', () => {
    const theoSpec = ghepTheoSpec(docBangSpec('### 2.2 Nhân viên', 4))
    expect(theoSpec.size).toBeGreaterThan(25)
    expect(congCu(MUC_NHAN_VIEN)).toEqual(theoSpec)
  })

  it('khu quản trị: đủ trang, đúng mã quyền (mục 2.3)', () => {
    const theoSpec = ghepTheoSpec(docBangSpec('### 2.3 Quản trị', 3))
    expect(theoSpec.size).toBeGreaterThanOrEqual(20)
    // Trang chủ quản trị ghi là "/ (dashboard)" trong spec
    const congCuQT = congCu(MUC_QUAN_TRI)
    expect(congCuQT.get('/')).toEqual(['report.all'])
    congCuQT.delete('/')
    const spec = new Map(theoSpec)
    spec.delete('/')
    expect(congCuQT).toEqual(spec)
  })

  it('khu cửa hàng: đủ trang như bảng ở mục 2.1', () => {
    const theoSpec = docBangSpec('### 2.1 Cửa hàng', 3)
      .flatMap((d) => d.duong)
      .map((d) => d.split('?')[0])
      .filter((d) => d !== '/')
    expect(theoSpec.length).toBeGreaterThan(20)
    expect(TRANG_CUA_HANG.map((t) => t.duong).sort()).toEqual([...theoSpec].sort())
  })

  it('mọi mã quyền dùng trên UI đều có trong quyen.yaml', () => {
    const maHopLe = new Set([...doc('docs/spec/data/quyen.yaml').matchAll(/^- ma: (\S+)/gm)].map((m) => m[1]))
    const dung = [...MUC_NHAN_VIEN, ...MUC_QUAN_TRI].flatMap((m) => m.quyen)
    expect(dung.filter((q) => !maHopLe.has(q))).toEqual([])
  })

  it('mỗi đường dẫn trong bảng có route thật, không rơi vào trang 404', () => {
    const routes = taoRoutes()
    const rotRoute = (goc: string, muc: readonly { duong: string }[]) =>
      muc
        .map((m) => (m.duong === '/' ? goc : goc + m.duong).replace(':id', '5'))
        .filter((u) => {
          const khop = matchRoutes(routes, u)
          return !khop || khop.at(-1)?.route.path === '*'
        })
    expect(rotRoute('/nhan-vien', MUC_NHAN_VIEN)).toEqual([])
    expect(rotRoute('/quan-tri', MUC_QUAN_TRI)).toEqual([])
    expect(rotRoute('', TRANG_CUA_HANG.map((t) => ({ duong: t.duong.replace(':slug', 'x').replace(':token', 'x').replace(':ma', 'x') })))).toEqual([])
  })
})

describe('khu cửa hàng', () => {
  it('trang chủ hiện layout cửa hàng với thanh tìm kiếm, giỏ hàng và đăng nhập', async () => {
    renderTai('/')
    expect(await screen.findByRole('heading', { name: /Nhà thuốc/ })).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Tìm thuốc/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Giỏ hàng/ })).toHaveAttribute('href', '/gio-hang')
    expect(screen.getByRole('link', { name: /Đăng nhập/ })).toHaveAttribute('href', '/dang-nhap')
  })

  it('khách đã đăng nhập thấy liên kết tài khoản thay vì đăng nhập', async () => {
    renderTai('/', { loai: 'khach' })
    expect(await screen.findByRole('link', { name: /Người dùng thử/ })).toHaveAttribute('href', '/tai-khoan')
    expect(screen.getByRole('button', { name: /Đăng xuất/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Đăng nhập/ })).not.toBeInTheDocument()
  })

  it('đường dẫn lạ hiện 404 ngay trong layout cửa hàng', async () => {
    renderTai('/khong-co-trang-nay')
    expect(await screen.findByText('Không tìm thấy trang')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Tìm thuốc/)).toBeInTheDocument()
  })

  it('các trang trong spec 2.1 có route (đang xây dựng) kèm mã chức năng', async () => {
    renderTai('/gui-don-thuoc')
    expect(await screen.findByText(/KVL08/)).toBeInTheDocument()
  })

  it('/403 hiện trang không có quyền', async () => {
    renderTai('/403')
    expect(await screen.findByText('Bạn không có quyền truy cập trang này')).toBeInTheDocument()
  })
})

describe('khu nhân viên', () => {
  beforeEach(() => {
    GET.mockReset()
    GET.mockImplementation(GET_MAC_DINH)
  })
  const duocSi = { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'order.view': 'day_du', 'pos.sell': 'day_du' } } as const

  it('chưa đăng nhập bị chuyển tới trang đăng nhập nội bộ', async () => {
    const { router } = renderTai('/nhan-vien/don-hang')
    expect(await screen.findByRole('heading', { name: 'Đăng nhập nội bộ' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/nhan-vien/dang-nhap')
  })

  it('phiên của khách không vào được khu nội bộ', async () => {
    renderTai('/nhan-vien/don-hang', { loai: 'khach' })
    expect(await screen.findByRole('heading', { name: 'Đăng nhập nội bộ' })).toBeInTheDocument()
  })

  it('menu chỉ có các mục người dùng có quyền', async () => {
    renderTai('/nhan-vien/don-hang', duocSi)
    const menu = await screen.findByRole('menu')
    expect(within(menu).getByText('Quản lý đơn')).toBeInTheDocument()
    expect(within(menu).getByText('Bán tại quầy')).toBeInTheDocument()
    expect(within(menu).queryByText('Nhà cung cấp')).not.toBeInTheDocument()
    expect(within(menu).queryByText('Tồn kho')).not.toBeInTheDocument()
  })

  it('trang có quyền hiện nội dung (đang xây dựng) kèm mã chức năng', async () => {
    renderTai('/nhan-vien/pos', duocSi)
    expect(await screen.findByText(/DS08/)).toBeInTheDocument()
  })

  it('trang không có quyền hiện 403 nhưng vẫn giữ layout và địa chỉ', async () => {
    const { router } = renderTai('/nhan-vien/ton-kho', duocSi)
    expect(await screen.findByText('Bạn không có quyền truy cập trang này')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/nhan-vien/ton-kho')
    expect(screen.getByRole('menu')).toBeInTheDocument()
  })

  it('quyền chỉ xem vẫn vào được trang xem', async () => {
    renderTai('/nhan-vien/thu-hoi', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'recall.contact': 'chi_xem' } })
    expect(await screen.findByText(/DS13/)).toBeInTheDocument()
  })

  it('/nhan-vien tự chuyển tới trang đầu tiên được phép', async () => {
    const { router } = renderTai('/nhan-vien', { loai: 'noi_bo', vaiTro: 'WAREHOUSE', quyen: { 'stock.view': 'day_du' } })
    await waitFor(() => expect(router.state.location.pathname).toBe('/nhan-vien/ton-kho'))
    expect(await screen.findByPlaceholderText('Tên hoặc SKU')).toBeInTheDocument()
  })

  it('tài khoản chưa được cấp quyền nào thì báo rõ thay vì trang trống', async () => {
    renderTai('/nhan-vien', { loai: 'noi_bo', vaiTro: 'WAREHOUSE', quyen: {} })
    expect(await screen.findByText(/chưa được cấp quyền/)).toBeInTheDocument()
  })

  it('Admin vào khu nhân viên bị đưa sang khu quản trị', async () => {
    const { router } = renderTai('/nhan-vien/don-hang', { loai: 'noi_bo', vaiTro: 'ADMIN', quyen: { 'order.view': 'chi_xem' } })
    await screen.findByRole('menu')
    expect(router.state.location.pathname).toBe('/quan-tri')
  })

  it('đường dẫn lạ trong khu nhân viên hiện 404 trong layout nội bộ', async () => {
    renderTai('/nhan-vien/khong-co', duocSi)
    expect(await screen.findByText('Không tìm thấy trang')).toBeInTheDocument()
    expect(screen.getByRole('menu')).toBeInTheDocument()
  })

  it('trang đăng nhập nội bộ truy cập được khi chưa đăng nhập', async () => {
    renderTai('/nhan-vien/dang-nhap')
    expect(await screen.findByRole('heading', { name: 'Đăng nhập nội bộ' })).toBeInTheDocument()
  })

  it('quyền đổi trên máy chủ thì menu của phiên đang mở cập nhật theo, không cần đăng nhập lại', async () => {
    GET.mockImplementation(async (duong: string) => {
      if (duong.endsWith('/noi-bo/toi')) {
        return {
          data: {
            id: 1,
            ma_nhan_vien: 'NV0001',
            ho_ten: 'Người dùng thử',
            email: 'x@example.com',
            so_dien_thoai: null,
            vai_tro: { ma: 'PHARMACIST', ten: 'Dược sĩ bán hàng' },
            phai_doi_mat_khau: false,
            quyen: { 'order.view': 'day_du', 'stock.view': 'chi_xem' }, // đã bỏ pos.sell, thêm stock.view
          },
        }
      }
      return duong.endsWith('/so-chua-doc') ? { data: { so_chua_doc: 0 } } : { data: { du_lieu: [], tong: 0, trang: 1, kich_thuoc: 10 } }
    })
    renderTai('/nhan-vien/don-hang', duocSi)
    const menu = await screen.findByRole('menu')
    await waitFor(() => expect(within(menu).getByText('Tồn kho')).toBeInTheDocument())
    expect(within(menu).queryByText('Bán tại quầy')).not.toBeInTheDocument()
    expect(usePhien.getState().quyen).toEqual({ 'order.view': 'day_du', 'stock.view': 'chi_xem' })
  })

  it('header có chuông thông báo lấy số chưa đọc từ API', async () => {
    GET.mockImplementationOnce(async () => ({ data: { so_chua_doc: 3 } }))
    renderTai('/nhan-vien/don-hang', duocSi)
    expect(await screen.findByRole('button', { name: 'Thông báo, 3 chưa đọc' })).toBeInTheDocument()
  })

  it('đăng xuất gọi API nội bộ, xóa phiên và về trang đăng nhập nội bộ', async () => {
    localStorage.clear()
    const { router } = renderTai('/nhan-vien/don-hang', duocSi)
    await userEvent.setup().click(await screen.findByRole('button', { name: /Người dùng thử/ }))
    await userEvent.setup().click(await screen.findByText('Đăng xuất'))
    await waitFor(() => expect(router.state.location.pathname).toBe('/nhan-vien/dang-nhap'))
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/auth/dang-xuat')
    expect(usePhien.getState().loai).toBeNull()
  })

  it('menu tài khoản dẫn tới trang hồ sơ và đổi mật khẩu', async () => {
    const { router } = renderTai('/nhan-vien/don-hang', duocSi)
    await userEvent.setup().click(await screen.findByRole('button', { name: /Người dùng thử/ }))
    await userEvent.setup().click(await screen.findByText('Hồ sơ và đổi mật khẩu'))
    await waitFor(() => expect(router.state.location.pathname).toBe('/nhan-vien/tai-khoan'))
    expect(await screen.findByRole('heading', { name: 'Tài khoản của tôi' })).toBeInTheDocument()
  })
})

describe('tài khoản bị bắt đổi mật khẩu', () => {
  const batDoi = { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'order.view': 'day_du' }, phaiDoiMatKhau: true } as const

  beforeEach(() => POST.mockClear())

  it.each(['/nhan-vien', '/nhan-vien/don-hang', '/nhan-vien/ton-kho'])('%s chuyển tới trang tài khoản', async (duong) => {
    const { router } = renderTai(duong, batDoi)
    expect(await screen.findByText('Bạn cần đổi mật khẩu trước khi tiếp tục')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/nhan-vien/tai-khoan')
  })

  it('Admin cũng bị chuyển từ khu quản trị', async () => {
    const { router } = renderTai('/quan-tri/nhan-vien', { ...batDoi, vaiTro: 'ADMIN' })
    expect(await screen.findByText('Bạn cần đổi mật khẩu trước khi tiếp tục')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/nhan-vien/tai-khoan')
  })

  it('không có menu để đi tiếp, chỉ có form đổi mật khẩu', async () => {
    renderTai('/nhan-vien/don-hang', batDoi)
    await screen.findByText('Bạn cần đổi mật khẩu trước khi tiếp tục')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Đổi mật khẩu' })).toBeInTheDocument()
  })

  it('chưa đăng nhập thì trang tài khoản chuyển tới đăng nhập nội bộ', async () => {
    const { router } = renderTai('/nhan-vien/tai-khoan')
    expect(await screen.findByRole('heading', { name: 'Đăng nhập nội bộ' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/nhan-vien/dang-nhap')
  })
})

describe('khu quản trị', () => {
  const admin = { loai: 'noi_bo', vaiTro: 'ADMIN', quyen: { 'report.all': 'day_du', 'order.view': 'chi_xem', 'staff.manage': 'day_du' } } as const

  it('Admin vào dashboard và thấy menu theo quyền', async () => {
    renderTai('/quan-tri', admin)
    const menu = await screen.findByRole('menu')
    expect(within(menu).getByText('Nhân viên')).toBeInTheDocument()
    expect(within(menu).getByText('Xem đơn hàng')).toBeInTheDocument()
    expect(within(menu).queryByText('Nhật ký hệ thống')).not.toBeInTheDocument()
    expect(await screen.findByText(/AD14/)).toBeInTheDocument()
  })

  it('dược sĩ không vào được khu quản trị dù có token nội bộ', async () => {
    renderTai('/quan-tri', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'order.view': 'day_du' } })
    expect(await screen.findByText('Bạn không có quyền truy cập trang này')).toBeInTheDocument()
  })

  it('vai trò khác ADMIN không vào được khu quản trị kể cả khi được cấp đúng mã quyền của trang', async () => {
    renderTai('/quan-tri', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'report.all': 'day_du' } })
    expect(await screen.findByText('Bạn không có quyền truy cập trang này')).toBeInTheDocument()
    expect(screen.queryByRole('menu')).not.toBeInTheDocument() // không dựng cả khung quản trị
    expect(screen.queryByText(/AD14/)).not.toBeInTheDocument()
  })

  it('chưa đăng nhập bị chuyển tới đăng nhập nội bộ', async () => {
    const { router } = renderTai('/quan-tri/nhan-vien')
    expect(await screen.findByRole('heading', { name: 'Đăng nhập nội bộ' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/nhan-vien/dang-nhap')
  })

  it('trang xem chỉ cần quyền mức xem', async () => {
    renderTai('/quan-tri/xem/don-hang', admin)
    expect(await screen.findByText(/AD16/)).toBeInTheDocument()
  })
})
