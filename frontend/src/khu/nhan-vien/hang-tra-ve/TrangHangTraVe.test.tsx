import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: vi.fn(), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const DONG = { ct_don_hang_id: 7, ten_san_pham: 'Panadol', ten_don_vi: 'hộp', he_so: 1, so_luong: 2, lo: [{ lo_id: 9, so_lo: 'L01', han_su_dung: '2027-01-01', so_luong_da_xuat: 2 }] }
const DT = { id: 3, ma_yeu_cau: 'DT0003', ma_don: 'DHABC', ly_do: 'hu_hong', mo_ta: null, ma_van_don: 'GIA1', anh: [], dong: [DONG] }
const HV = { id: 5, ma_don: 'DHXYZ', trang_thai: 'hoan_ve_kho', da_thanh_toan: true, dong: [DONG] }
const dung = () => renderTai('/nhan-vien/hang-tra-ve', { loai: 'noi_bo', vaiTro: 'WAREHOUSE', quyen: { 'return.receive': 'day_du' } as never })

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong.endsWith('/nhan-hang/doi-tra')) return ok([DT])
    if (duong.endsWith('/nhan-hang/hoan-ve')) return ok([HV])
    return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
  })
  POST.mockResolvedValue(ok({ ma_don: 'DHXYZ', trang_thai: 'da_huy', cho_hoan_tien: true, so_luong_hoan_nhap: 2, so_luong_biet_tru: 0 }))
})

describe('Nhận hàng trả về (KHO10)', () => {
  it('nhận hàng khách trả: tự chọn lô duy nhất, cần kết quả kiểm mới gửi được', async () => {
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Nhận hàng'))
    const gui = await screen.findByText('Xác nhận đã nhận')
    expect(gui.closest('button')).toBeDisabled()
    await u.type(screen.getByLabelText('Kết quả kiểm hàng'), 'Đúng mô tả')
    await waitFor(() => expect(gui.closest('button')).toBeEnabled())
    await u.click(gui)
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/nhan-hang/doi-tra/{yc_id}')
    expect(POST.mock.calls[0][1].body).toEqual({ ket_qua_kiem_hang: 'Đúng mô tả', dong: [{ ct_don_hang_id: 7, lo_id: 9, so_luong_nhan: 2 }] })
  })

  it('kiểm hàng hoàn về kho gửi tình trạng từng dòng', async () => {
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText(/Đơn hoàn về kho/))
    await u.click(await screen.findByText('Kiểm hàng'))
    await u.click(await screen.findByText('Hư hỏng'))
    await u.click(await screen.findByText('Xác nhận và hủy đơn'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/nhan-hang/hoan-ve/{don_id}')
    expect(POST.mock.calls[0][1].body).toEqual({ dong: [{ ct_don_hang_id: 7, tinh_trang: 'hu_hong' }] })
  })
})
