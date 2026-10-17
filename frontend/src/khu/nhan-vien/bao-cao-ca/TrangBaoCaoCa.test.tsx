import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const CA = { tu: '2026-10-16T01:00:00Z', den: '2026-10-16T10:00:00Z', so_don: 7, doanh_thu: '1250000.00', so_don_thuoc_da_duyet: 3, tien_mat_thu_tai_quay: '800000.00', chuyen_khoan_thu_tai_quay: '200000.00', so_giao_dich_tien_mat: 5 }
const dung = () => renderTai('/nhan-vien/bao-cao-ca', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'report.shift': 'day_du' } as never })

beforeEach(() => {
  GET.mockReset()
  GET.mockImplementation(async (d: string) => (d === '/api/v1/noi-bo/bao-cao/ca' ? ok(CA) : ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })))
})

describe('Báo cáo ca (DS14)', () => {
  it('hiện số liệu của ca, tiền mặt thu tại quầy và không có giá vốn/lợi nhuận', async () => {
    dung()
    expect(await screen.findByText('Số đơn do tôi xử lý')).toBeInTheDocument()
    expect(screen.getByText(/1\.250\.000/)).toBeInTheDocument()
    expect(screen.getByText(/800\.000.*5 giao dịch/)).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.queryByText(/giá vốn|lợi nhuận/i, { selector: 'th, td, .ant-descriptions-item-label' })).not.toBeInTheDocument()
    const goi = GET.mock.calls.find((c) => c[0] === '/api/v1/noi-bo/bao-cao/ca')!
    expect(goi[1].params.query.tu).toMatch(/^\d{4}-\d{2}-\d{2}T/)
  })

  it('lỗi thì báo lỗi', async () => {
    GET.mockImplementation(async (d: string) => (d === '/api/v1/noi-bo/bao-cao/ca' ? { error: { ma_loi: 'DU_LIEU_KHONG_HOP_LE', thong_diep: 'x', chi_tiet: null }, response: { ok: false, status: 400 } } : ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })))
    dung()
    expect(await screen.findByText(/Không tải được báo cáo ca/)).toBeInTheDocument()
  })
})
