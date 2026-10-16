import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'
import { loiAnhTraCuu } from './traCuuAnh'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: vi.fn(), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const THE = { id: 1, ten: 'Panadol Extra', slug: 'panadol-extra', loai_san_pham: 'thuoc_khong_ke_don', can_tu_van: false, thuong_hieu: null, quy_cach: null, anh_chinh_url: null, gia: '25000.00', ten_don_vi_gia: 'hộp', con_hang: true }
const DOC = { ten_san_pham: 'Panadol Extra', hoat_chat: [{ ten: 'Paracetamol', ham_luong: '500 mg' }], so_dang_ky: 'VD-12345-20', nha_san_xuat: 'GSK', dang_bao_che: 'viên nén', do_tin_cay: 0.9 }
const anh = (ten = 'hop.jpg', loai = 'image/jpeg') => new File([new Uint8Array([1, 2, 3])], ten, { type: loai })

beforeEach(() => {
  GET.mockReset(); POST.mockReset()
  GET.mockImplementation(async () => ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 20 }))
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:xem', revokeObjectURL: () => {} }))
})

describe('lib: kiểm tra ảnh tra cứu', () => {
  it.each([
    [{ type: 'image/jpeg', size: 10 }, null],
    [{ type: 'image/png', size: 5 * 1024 * 1024 }, null],
    [{ type: 'image/heic', size: 10 }, 'Chỉ nhận ảnh JPEG, PNG hoặc WebP'],
    [{ type: 'image/webp', size: 5 * 1024 * 1024 + 1 }, 'Ảnh tối đa 5 MB'],
    [{ type: 'image/jpeg', size: 0 }, 'Ảnh trống'],
  ])('%j -> %s', (f, mong) => expect(loiAnhTraCuu(f)).toBe(mong))
})

describe('Tra cứu thuốc bằng ảnh (KVL06)', () => {
  it('chọn ảnh rồi tra cứu: gửi multipart, hiện sản phẩm đã xác minh kèm tóm tắt', async () => {
    POST.mockResolvedValue(ok({ doc_duoc: DOC, khop: { cach: 'so_dang_ky', san_pham: THE, la_thuoc_ke_don: false, tom_tat: { chi_dinh: 'Giảm đau, hạ sốt', chong_chi_dinh: null, than_trong: 'Bệnh gan' } }, da_xac_minh: true, canh_bao: null }))
    renderTai('/tra-cuu-anh')
    const u = userEvent.setup()
    expect(await screen.findByText('Tra cứu thuốc bằng ảnh', { selector: 'h2' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Tra cứu/ })).toBeDisabled()
    await u.upload(screen.getByTestId('chon-anh'), anh())
    expect(await screen.findByAltText('Ảnh hộp thuốc đã chọn')).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: /Tra cứu/ }))
    expect(await screen.findByText('Giảm đau, hạ sốt')).toBeInTheDocument()
    expect(screen.getByText('Đã xác minh')).toBeInTheDocument()
    expect(screen.getByText('Bệnh gan')).toBeInTheDocument()
    expect(screen.getByText('Paracetamol 500 mg')).toBeInTheDocument()
    const goi = POST.mock.calls[0]
    expect(goi[0]).toBe('/api/v1/tra-cuu-anh')
    const fd = goi[1].bodySerializer() as FormData
    expect((fd.get('anh') as File).name).toBe('hop.jpg')
  })

  it('không khớp: chỉ hiện thông tin đọc được kèm cảnh báo chưa xác minh', async () => {
    POST.mockResolvedValue(ok({ doc_duoc: DOC, khop: null, da_xac_minh: false, canh_bao: 'Chưa xác minh: sản phẩm này không có trong hệ thống nhà thuốc.' }))
    renderTai('/tra-cuu-anh')
    const u = userEvent.setup()
    await u.upload(await screen.findByTestId('chon-anh'), anh())
    await u.click(screen.getByRole('button', { name: /Tra cứu/ }))
    expect(await screen.findByText(/không có trong hệ thống nhà thuốc/)).toBeInTheDocument()
    expect(screen.getAllByText('Chưa xác minh').length).toBeGreaterThan(0)
    expect(screen.queryByText('Sản phẩm trong nhà thuốc')).not.toBeInTheDocument()
    expect(screen.getByText('GSK')).toBeInTheDocument()
  })

  it('thuốc kê đơn: có cảnh báo, không có tóm tắt công dụng', async () => {
    POST.mockResolvedValue(ok({ doc_duoc: DOC, khop: { cach: 'so_dang_ky', san_pham: { ...THE, loai_san_pham: 'thuoc_ke_don', can_tu_van: true }, la_thuoc_ke_don: true, tom_tat: null }, da_xac_minh: true, canh_bao: 'Đây là thuốc kê đơn: chỉ dùng khi có chỉ định của bác sĩ.' }))
    renderTai('/tra-cuu-anh')
    const u = userEvent.setup()
    await u.upload(await screen.findByTestId('chon-anh'), anh())
    await u.click(screen.getByRole('button', { name: /Tra cứu/ }))
    expect(await screen.findByText(/thuốc kê đơn: chỉ dùng khi có chỉ định/)).toBeInTheDocument()
    expect(screen.queryByText('Chỉ định')).not.toBeInTheDocument()
  })

  it('ảnh sai định dạng bị từ chối ở client, không gọi API', async () => {
    renderTai('/tra-cuu-anh')
    const u = userEvent.setup({ applyAccept: false })
    await u.upload(await screen.findByTestId('chon-anh'), anh('a.heic', 'image/heic'))
    expect(await screen.findByText('Chỉ nhận ảnh JPEG, PNG hoặc WebP')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Tra cứu/ })).toBeDisabled()
    expect(POST).not.toHaveBeenCalled()
  })

  it('máy chủ báo lỗi (hết lượt, AI lỗi) thì hiện thông điệp', async () => {
    POST.mockResolvedValue({ error: { ma_loi: 'QUA_GIOI_HAN', thong_diep: 'Bạn tra cứu ảnh quá nhiều, vui lòng chờ một lúc rồi thử lại', chi_tiet: null }, response: { ok: false, status: 429 } })
    renderTai('/tra-cuu-anh')
    const u = userEvent.setup()
    await u.upload(await screen.findByTestId('chon-anh'), anh())
    await u.click(screen.getByRole('button', { name: /Tra cứu/ }))
    await waitFor(() => expect(screen.getByText(/quá nhiều/)).toBeInTheDocument())
  })

  it('thanh tìm kiếm có nút máy ảnh dẫn tới trang tra cứu', async () => {
    const { router } = renderTai('/gio-hang')
    const u = userEvent.setup()
    await u.click(await screen.findByLabelText('Tra cứu thuốc bằng ảnh'))
    await waitFor(() => expect(router.state.location.pathname).toBe('/tra-cuu-anh'))
  })
})
