import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const PUT = vi.fn()
const DELETE = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn(), PUT: (...a: unknown[]) => PUT(...a), DELETE: (...a: unknown[]) => DELETE(...a) },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const CHUA_CO = { dong_y_su_dung: false, dong_y_luc: null, nam_sinh: null, benh_nen: null, dang_mang_thai: null, dang_cho_con_bu: null, di_ung: [] }
const DA_CO = {
  dong_y_su_dung: true, dong_y_luc: '2026-10-16T01:00:00Z', nam_sinh: 1990, benh_nen: 'tiểu đường',
  dang_mang_thai: false, dang_cho_con_bu: false, di_ung: [{ hoat_chat_id: 7, ten_hoat_chat: 'Amoxicillin', ghi_chu: null }],
}
let hoSo: unknown

beforeEach(() => {
  for (const m of [GET, PUT, DELETE]) m.mockReset()
  hoSo = CHUA_CO
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/toi/ho-so-suc-khoe') return ok(hoSo)
    if (duong === '/api/v1/toi/ho-so-suc-khoe/hoat-chat') return ok([{ id: 7, ten: 'Amoxicillin' }])
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('Hồ sơ sức khỏe (KTV11)', () => {
  it('khách chưa đăng nhập bị chuyển tới trang đăng nhập', async () => {
    const { router } = renderTai('/tai-khoan/suc-khoe')
    await waitFor(() => expect(router.state.location.pathname).toBe('/dang-nhap'))
  })

  it('chưa có hồ sơ: hiện màn đồng ý, chưa có form; bấm đồng ý mới hiện form', async () => {
    renderTai('/tai-khoan/suc-khoe', { loai: 'khach' })
    expect(await screen.findByTestId('man-dong-y')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Lưu hồ sơ' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Tôi đồng ý' }))
    expect(await screen.findByRole('button', { name: 'Lưu hồ sơ' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Xóa hồ sơ' })).not.toBeInTheDocument()
  })

  it('lưu gửi dong_y_su_dung = true kèm bệnh nền', async () => {
    PUT.mockResolvedValue(ok(DA_CO))
    renderTai('/tai-khoan/suc-khoe', { loai: 'khach' })
    await userEvent.click(await screen.findByRole('button', { name: 'Tôi đồng ý' }))
    await userEvent.type(await screen.findByLabelText('Bệnh nền'), 'huyết áp cao')
    await userEvent.click(screen.getByRole('button', { name: 'Lưu hồ sơ' }))
    await waitFor(() => expect(PUT).toHaveBeenCalled())
    const body = PUT.mock.calls[0][1].body
    expect(body).toMatchObject({ dong_y_su_dung: true, benh_nen: 'huyết áp cao', di_ung: [] })
  })

  it('đã có hồ sơ: hiện dữ liệu và nút xóa gọi DELETE sau khi xác nhận', async () => {
    hoSo = DA_CO
    DELETE.mockResolvedValue({ response: { ok: true, status: 204 } })
    renderTai('/tai-khoan/suc-khoe', { loai: 'khach' })
    expect(await screen.findByDisplayValue('tiểu đường')).toBeInTheDocument()
    expect(screen.getByText('Amoxicillin')).toBeInTheDocument()
    expect(screen.queryByTestId('man-dong-y')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Xóa hồ sơ' }))
    hoSo = CHUA_CO
    await userEvent.click(await screen.findByRole('button', { name: 'Xóa' }))
    await waitFor(() => expect(DELETE).toHaveBeenCalled())
    expect(await screen.findByTestId('man-dong-y')).toBeInTheDocument()
  })
})
