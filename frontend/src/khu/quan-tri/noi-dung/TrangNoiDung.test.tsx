import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangNoiDung from './TrangNoiDung'
import type { BaiVietAdmin, BannerRa } from './noiDungWeb'

vi.setConfig({ testTimeout: 90_000 }) // antd + jsdom chậm; CI chỉ có 2 vCPU mà chạy song song nhiều file

const GET = vi.fn()
const POST = vi.fn()
const PATCH = vi.fn()
const DELETE = vi.fn()
vi.mock('../../../api/client', () => ({
  api: {
    GET: (...a: unknown[]) => GET(...a),
    POST: (...a: unknown[]) => POST(...a),
    PATCH: (...a: unknown[]) => PATCH(...a),
    DELETE: (...a: unknown[]) => DELETE(...a),
  },
}))

const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({ error: { ma_loi, thong_diep, chi_tiet }, response: { ok: false, status } })

const BANNER: BannerRa = {
  id: 1,
  tieu_de: 'Khuyến mãi hè',
  anh_url: '/api/v1/tep/banner/a.jpg',
  lien_ket: '/danh-muc/thuoc',
  vi_tri: 'trang_chu_chinh',
  thu_tu: 2,
  bat_dau: null,
  ket_thuc: null,
  dang_hien: true,
  tinh_trang: 'dang_hien',
  phien_ban: 'aaaaaaaaaaaaaaaa',
}
const BAI: BaiVietAdmin = {
  id: 7,
  tieu_de: 'Phòng cảm cúm',
  slug: 'phong-cam-cum',
  loai: 'bai_viet',
  trang_thai: 'da_duyet',
  dua_vao_ai: false,
  tac_gia: 'Admin Một',
  created_at: '2026-10-10T03:00:00Z',
  updated_at: null,
  ngay_duyet: '2026-10-11T03:00:00Z',
  noi_dung: 'Rửa tay thường xuyên.',
  anh_bia_url: null,
  duoc_si_duyet: 'Dược Sĩ',
  phien_ban: 'bbbbbbbbbbbbbbbb',
}
const TOM_TAT = (b: BaiVietAdmin) => {
  const { noi_dung: _a, anh_bia_url: _b, duoc_si_duyet: _c, phien_ban: _d, ...tom } = b
  return tom
}

let banners: BannerRa[]
let bai: BaiVietAdmin[]

function dung(quyen: Record<string, 'day_du' | 'chi_xem'> = { 'cms.manage': 'day_du' }) {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'AD', vaiTro: 'ADMIN' }, quyen })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter>
            <TrangNoiDung />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  PATCH.mockReset()
  DELETE.mockReset()
  banners = [BANNER]
  bai = [BAI]
  GET.mockImplementation(async (duong: string, tham?: { params?: { path?: { bai_viet_id?: number }; query?: Record<string, unknown> } }) => {
    if (duong === '/api/v1/noi-bo/banner') return ok(banners)
    if (duong === '/api/v1/noi-bo/bai-viet') {
      const loai = tham?.params?.query?.loai
      const du_lieu = bai.filter((b) => b.loai === loai).map(TOM_TAT)
      return ok({ du_lieu, tong: du_lieu.length, trang: 1, kich_thuoc: 20 })
    }
    if (duong === '/api/v1/noi-bo/bai-viet/{bai_viet_id}') return ok(bai.find((b) => b.id === tham?.params?.path?.bai_viet_id))
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('Banner', () => {
  it('liệt kê banner kèm tình trạng; quyền đầy đủ có nút thêm/sửa/xóa, chỉ xem thì không', async () => {
    banners = [BANNER, { ...BANNER, id: 2, tieu_de: 'Hết hạn', tinh_trang: 'het_han', phien_ban: 'cccccccccccccccc' }]
    const { unmount } = dung()
    const hang = (await screen.findByText('Khuyến mãi hè')).closest('tr') as HTMLElement
    expect(within(hang).getByText('Đang hiển thị')).toBeInTheDocument()
    expect(within(hang).getByText('Trang chủ: banner chính')).toBeInTheDocument()
    expect(within(hang).getByText('Luôn hiển thị')).toBeInTheDocument()
    expect(within((await screen.findByText('Hết hạn')).closest('tr') as HTMLElement).getByText('Đã hết hạn')).toBeInTheDocument()
    expect(screen.getByText('Thêm banner')).toBeInTheDocument()
    expect(within(hang).getByText('Sửa')).toBeInTheDocument()
    unmount()
    dung({ 'cms.manage': 'chi_xem' })
    const hangXem = (await screen.findByText('Khuyến mãi hè')).closest('tr') as HTMLElement
    expect(within(hangXem).queryByText('Sửa')).not.toBeInTheDocument()
    expect(screen.queryByText('Thêm banner')).not.toBeInTheDocument()
  })

  it('thêm banner: báo lỗi thiếu ảnh, tải ảnh lên, rồi lưu đúng thân', async () => {
    banners = []
    POST.mockImplementation(async (duong: string) => (duong.endsWith('/anh') ? ok({ url: '/api/v1/tep/banner/moi.jpg' }) : ok({ ...BANNER, id: 9 })))
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Thêm banner'))
    const hop = await screen.findByRole('dialog')
    await u.click(within(hop).getByText('Lưu'))
    expect(await within(hop).findByText('Vui lòng chọn ảnh')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()

    const tep = new File([new Uint8Array([0xff, 0xd8, 0xff, 0xe0])], 'a.jpg', { type: 'image/jpeg' })
    await u.upload(within(hop).getByLabelText('Chọn ảnh để tải lên'), tep)
    await waitFor(() => expect(within(hop).getByAltText('Ảnh đã chọn')).toHaveAttribute('src', '/api/v1/tep/banner/moi.jpg'))
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/banner/anh')
    await u.type(within(hop).getByLabelText(/Tiêu đề/), '  Giảm  giá ')
    await u.type(within(hop).getByLabelText(/Liên kết khi bấm/), '/danh-muc/thuoc')
    await u.click(within(hop).getByText('Lưu'))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(2))
    expect(POST.mock.calls[1][0]).toBe('/api/v1/noi-bo/banner')
    expect(POST.mock.calls[1][1].body).toEqual({
      tieu_de: 'Giảm giá',
      anh_url: '/api/v1/tep/banner/moi.jpg',
      lien_ket: '/danh-muc/thuoc',
      vi_tri: 'trang_chu_chinh',
      thu_tu: 0,
      bat_dau: null,
      ket_thuc: null,
      dang_hien: true,
    })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('liên kết nguy hiểm bị chặn ở form, không gọi API', async () => {
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Sửa'))
    const hop = await screen.findByRole('dialog')
    const lienKet = within(hop).getByLabelText(/Liên kết khi bấm/)
    await u.clear(lienKet)
    await u.type(lienKet, 'javascript:alert(1)')
    await u.click(within(hop).getByText('Lưu'))
    expect(await within(hop).findByText(/Đường dẫn phải bắt đầu bằng/)).toBeInTheDocument()
    expect(PATCH).not.toHaveBeenCalled()
  })

  it('sửa banner chỉ gửi trường đã đổi cùng phien_ban', async () => {
    PATCH.mockResolvedValue(ok({ ...BANNER, thu_tu: 5 }))
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Sửa'))
    const hop = await screen.findByRole('dialog')
    expect(within(hop).getByLabelText(/Tiêu đề/)).toHaveValue('Khuyến mãi hè')
    const thuTu = within(hop).getByLabelText('Thứ tự')
    await u.clear(thuTu)
    await u.type(thuTu, '5')
    await u.click(within(hop).getByText('Lưu'))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(1))
    expect(PATCH.mock.calls[0][1].body).toEqual({ phien_ban: 'aaaaaaaaaaaaaaaa', thu_tu: 5 })
    expect(PATCH.mock.calls[0][1].params.path).toEqual({ banner_id: 1 })
  })

  it('409: form lấy bản mới của máy chủ nhưng giữ phần mình vừa sửa, lưu lại gửi phien_ban mới', async () => {
    const moi: BannerRa = { ...BANNER, tieu_de: 'Người khác đổi', phien_ban: 'dddddddddddddddd' }
    PATCH.mockResolvedValueOnce(loi(409, 'DU_LIEU_DA_THAY_DOI', 'Đã thay đổi')).mockResolvedValueOnce(ok(moi))
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Sửa'))
    const hop = await screen.findByRole('dialog')
    const thuTu = within(hop).getByLabelText('Thứ tự')
    await u.clear(thuTu)
    await u.type(thuTu, '8')
    banners = [moi] // trong lúc đó người khác đổi tiêu đề
    await u.click(within(hop).getByText('Lưu'))
    expect(await within(hop).findByText(/Banner đã được người khác thay đổi/)).toBeInTheDocument()
    expect(within(hop).getByLabelText(/Tiêu đề/)).toHaveValue('Người khác đổi') // lấy theo bản mới
    expect(within(hop).getByLabelText('Thứ tự')).toHaveValue('8') // giữ phần mình sửa
    await u.click(within(hop).getByText('Lưu'))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(2))
    expect(PATCH.mock.calls[1][1].body).toEqual({ phien_ban: 'dddddddddddddddd', thu_tu: 8 }) // không ghi đè tiêu đề của người kia
  })

  it('xóa banner: xác nhận rồi gửi phien_ban', async () => {
    DELETE.mockResolvedValue({ response: { ok: true, status: 204 } })
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Xóa'))
    await u.click((await waitFor(() => document.querySelector('.ant-popover .ant-btn-primary'))) as HTMLElement)
    await waitFor(() => expect(DELETE).toHaveBeenCalledTimes(1))
    expect(DELETE.mock.calls[0][1].params).toEqual({ path: { banner_id: 1 }, query: { phien_ban: 'aaaaaaaaaaaaaaaa' } })
  })
})

describe('Bài viết, chính sách, FAQ', () => {
  const mo = async (ten: string) => {
    const u = userEvent.setup()
    await u.click(await screen.findByRole('tab', { name: ten }))
    return u
  }

  it('liệt kê bài theo loại với nhãn trạng thái đúng: bài sức khỏe chờ duyệt khác với bản nháp chính sách', async () => {
    bai = [
      BAI,
      { ...BAI, id: 8, tieu_de: 'Bài chờ', trang_thai: 'nhap', ngay_duyet: null },
      { ...BAI, id: 9, tieu_de: 'Bài đã gỡ', trang_thai: 'luu_tru' },
      { ...BAI, id: 10, tieu_de: 'Chính sách nháp', loai: 'chinh_sach', trang_thai: 'nhap' },
    ]
    dung()
    await mo('Bài viết sức khỏe')
    const hangCho = (await screen.findByText('Bài chờ')).closest('tr') as HTMLElement
    expect(within(hangCho).getByText('Chờ dược sĩ duyệt')).toBeInTheDocument()
    expect(within((await screen.findByText('Bài đã gỡ')).closest('tr') as HTMLElement).getByText('Đăng lại')).toBeInTheDocument()
    expect(within((await screen.findByText('Phòng cảm cúm')).closest('tr') as HTMLElement).getByText('Đang đăng')).toBeInTheDocument()
    expect(GET.mock.calls.some((c) => c[0] === '/api/v1/noi-bo/bai-viet' && c[1].params.query.loai === 'bai_viet')).toBe(true)
    await mo('Chính sách')
    expect(within((await screen.findByText('Chính sách nháp')).closest('tr') as HTMLElement).getByText('Bản nháp')).toBeInTheDocument()
  })

  it('soạn bài sức khỏe: báo lỗi trống, rồi lưu và nói rõ bài chờ dược sĩ duyệt', async () => {
    bai = []
    POST.mockResolvedValue(ok({ ...BAI, id: 11, trang_thai: 'nhap' }))
    dung()
    const u = await mo('Bài viết sức khỏe')
    await u.click(await screen.findByText(/Soạn bài viết mới/))
    const khung = await screen.findByRole('dialog')
    expect(within(khung).getByText(/cần dược sĩ duyệt mới hiện trên website/)).toBeInTheDocument()
    await u.click(within(khung).getByText('Lưu'))
    expect(await within(khung).findByText('Vui lòng nhập tiêu đề')).toBeInTheDocument()
    expect(within(khung).getByText('Vui lòng nhập nội dung')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
    await u.type(within(khung).getByLabelText(/Tiêu đề/), 'Cách rửa tay')
    await u.type(within(khung).getByLabelText('Nội dung'), '## Bước 1{Enter}Làm ướt tay.')
    await u.click(within(khung).getByRole('tab', { name: 'Xem trước' }))
    expect(await within(khung).findByRole('heading', { name: 'Bước 1', level: 2 })).toBeInTheDocument()
    await u.click(within(khung).getByText('Lưu'))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST.mock.calls[0][1].body).toEqual({ loai: 'bai_viet', tieu_de: 'Cách rửa tay', noi_dung: '## Bước 1\nLàm ướt tay.', anh_bia_url: null, dua_vao_ai: false })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('sửa bài đang đăng: cảnh báo về chờ duyệt chỉ khi đổi nội dung, và chỉ gửi trường đã đổi', async () => {
    PATCH.mockResolvedValue(ok({ ...BAI, trang_thai: 'nhap', noi_dung: 'Nội dung mới' }))
    dung()
    const u = await mo('Bài viết sức khỏe')
    await u.click(await screen.findByText('Sửa'))
    const khung = await screen.findByRole('dialog')
    const noiDung = await within(khung).findByLabelText('Nội dung')
    expect(noiDung).toHaveValue('Rửa tay thường xuyên.')
    expect(within(khung).queryByText(/sẽ đưa bài về chờ dược sĩ duyệt/)).not.toBeInTheDocument()
    await u.click(within(khung).getByRole('switch')) // chỉ đổi dua_vao_ai: vẫn không cảnh báo
    expect(within(khung).queryByText(/sẽ đưa bài về chờ dược sĩ duyệt/)).not.toBeInTheDocument()
    await u.clear(noiDung)
    await u.type(noiDung, 'Nội dung mới')
    expect(await within(khung).findByText(/sẽ đưa bài về chờ dược sĩ duyệt/)).toBeInTheDocument()
    await u.click(within(khung).getByText('Lưu'))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(1))
    expect(PATCH.mock.calls[0][1].body).toEqual({ phien_ban: 'bbbbbbbbbbbbbbbb', noi_dung: 'Nội dung mới', dua_vao_ai: true })
  })

  it('gỡ bài: đọc phien_ban mới nhất rồi gửi; đăng lại bài đã gỡ', async () => {
    bai = [BAI, { ...BAI, id: 9, tieu_de: 'Bài đã gỡ', trang_thai: 'luu_tru', phien_ban: 'eeeeeeeeeeeeeeee' }]
    POST.mockResolvedValue(ok({ ...BAI, trang_thai: 'luu_tru' }))
    dung()
    const u = await mo('Bài viết sức khỏe')
    const hang = (await screen.findByText('Phòng cảm cúm')).closest('tr') as HTMLElement
    await u.click(within(hang).getByText('Gỡ'))
    await u.click(document.querySelector('.ant-popover .ant-btn-primary') as HTMLElement)
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/bai-viet/{bai_viet_id}/go')
    expect(POST.mock.calls[0][1].body).toEqual({ phien_ban: 'bbbbbbbbbbbbbbbb' })
    await u.click(within((await screen.findByText('Bài đã gỡ')).closest('tr') as HTMLElement).getByText('Đăng lại'))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(2))
    expect(POST.mock.calls[1][0]).toBe('/api/v1/noi-bo/bai-viet/{bai_viet_id}/dang')
    expect(POST.mock.calls[1][1].body).toEqual({ phien_ban: 'eeeeeeeeeeeeeeee' })
  })

  it('gỡ bài mà bài vừa bị người khác sửa: không gửi, báo và tải lại danh sách', async () => {
    dung()
    const u = await mo('Bài viết sức khỏe')
    const hang = (await screen.findByText('Phòng cảm cúm')).closest('tr') as HTMLElement
    bai = [{ ...BAI, noi_dung: 'Người khác vừa sửa', updated_at: '2026-10-12T03:00:00Z', phien_ban: 'ffffffffffffffff' }]
    await u.click(within(hang).getByText('Gỡ'))
    await u.click(document.querySelector('.ant-popover .ant-btn-primary') as HTMLElement)
    expect(await screen.findByText(/vừa được người khác thay đổi/)).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('chỉ xem: không có nút soạn, sửa, gỡ', async () => {
    dung({ 'cms.manage': 'chi_xem' })
    await mo('Bài viết sức khỏe')
    const hang = (await screen.findByText('Phòng cảm cúm')).closest('tr') as HTMLElement
    expect(within(hang).queryByText('Sửa')).not.toBeInTheDocument()
    expect(within(hang).queryByText('Gỡ')).not.toBeInTheDocument()
    expect(screen.queryByText(/Soạn bài viết mới/)).not.toBeInTheDocument()
  })
})
