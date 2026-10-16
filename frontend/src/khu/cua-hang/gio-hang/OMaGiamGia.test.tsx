import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App } from 'antd'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OMaGiamGia } from './OMaGiamGia'

const POST = vi.fn()
vi.mock('../../../api/client', () => ({ api: { POST: (...a: unknown[]) => POST(...a) } }))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const KQ = { hop_le: true, ma: 'SALE10', khuyen_mai: { ten: 'Sale 10%', loai_giam: 'phan_tram', gia_tri: '10.00', giam_toi_da: null, don_toi_thieu: '0.00' }, co_so_giam: '60000.00', giam: '6000.00', ma_ly_do: null, ly_do: null }

beforeEach(() => POST.mockReset())
const dung = (khiDoi = vi.fn()) => render(<App><OMaGiamGia khiDoi={khiDoi} /></App>)

describe('OMaGiamGia (KTV04)', () => {
  it('mã hợp lệ: hiện số tiền giảm, báo lên trang cha; gõ lại thì xóa kết quả', async () => {
    POST.mockResolvedValue(ok(KQ))
    const khiDoi = vi.fn()
    dung(khiDoi)
    const u = userEvent.setup()
    await u.type(screen.getByLabelText('Mã giảm giá'), 'sale10')
    await u.click(screen.getByRole('button', { name: 'Áp dụng' }))
    expect(await screen.findByText(/Sale 10%: giảm 6\.000/)).toBeInTheDocument()
    expect(POST).toHaveBeenCalledWith('/api/v1/toi/ma-giam-gia/kiem-tra', { body: { ma: 'sale10' } })
    expect(khiDoi).toHaveBeenLastCalledWith(expect.objectContaining({ giam: '6000.00' }))
    await u.type(screen.getByLabelText('Mã giảm giá'), 'x')
    expect(screen.queryByText(/giảm 6\.000/)).not.toBeInTheDocument()
    expect(khiDoi).toHaveBeenLastCalledWith(null)
  })

  it('mã không áp dụng được: hiện lý do', async () => {
    POST.mockResolvedValue(ok({ ...KQ, hop_le: false, giam: '0.00', ma_ly_do: 'het_han', ly_do: 'Mã giảm giá đã hết hạn' }))
    const khiDoi = vi.fn()
    dung(khiDoi)
    await userEvent.type(screen.getByLabelText('Mã giảm giá'), 'CU')
    await userEvent.click(screen.getByRole('button', { name: 'Áp dụng' }))
    expect(await screen.findByText('Mã giảm giá đã hết hạn')).toBeInTheDocument()
    await waitFor(() => expect(khiDoi).toHaveBeenLastCalledWith(null))
  })

  it('bị giới hạn tần suất thì báo chờ', async () => {
    POST.mockResolvedValue({ error: { ma_loi: 'QUA_GIOI_HAN', thong_diep: 'Bạn thử mã quá nhiều lần', chi_tiet: { thu_lai_sau_giay: 120 } }, response: { ok: false, status: 429 } })
    dung()
    await userEvent.type(screen.getByLabelText('Mã giảm giá'), 'A')
    await userEvent.click(screen.getByRole('button', { name: 'Áp dụng' }))
    expect(await screen.findByText(/thử lại sau 2 phút/)).toBeInTheDocument()
  })
})
