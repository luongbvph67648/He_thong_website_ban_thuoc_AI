import { describe, expect, it } from 'vitest'
import { guiTuForm, moTaMucGiam } from './khuyenMai'

const moc = (s: string) => ({ toISOString: () => s })
const nen = { ten: 'KM', loai_giam: 'phan_tram', gia_tri: 10, thoi_gian: [moc('2026-01-01T00:00:00Z'), moc('2026-02-01T00:00:00Z')], luot_moi_khach: 1, dang_hoat_dong: true } as const

describe('guiTuForm', () => {
  it('chỉ gửi phạm vi và trần giảm đúng loại', () => {
    const a = guiTuForm({ ...nen, pham_vi: 'danh_muc', danh_muc_ids: [1, 2], san_pham_ids: [9], giam_toi_da: 5000 })
    expect(a.danh_muc_ids).toEqual([1, 2])
    expect(a.san_pham_ids).toEqual([])
    expect(a.giam_toi_da).toBe('5000')
    const b = guiTuForm({ ...nen, loai_giam: 'so_tien', gia_tri: 20000, pham_vi: 'toan_bo', danh_muc_ids: [1], giam_toi_da: 5000 })
    expect(b.giam_toi_da).toBeNull()
    expect(b.danh_muc_ids).toEqual([])
    expect(b.gia_tri).toBe('20000')
    expect(b.bat_dau).toBe('2026-01-01T00:00:00Z')
  })
})

describe('moTaMucGiam', () => {
  const tien = (v: string) => `${Number(v)}đ`
  it('mô tả phần trăm có trần và số tiền', () => {
    expect(moTaMucGiam({ loai_giam: 'phan_tram', gia_tri: '10.00', giam_toi_da: '50000.00' }, tien)).toBe('10% (tối đa 50000đ)')
    expect(moTaMucGiam({ loai_giam: 'phan_tram', gia_tri: '7.50', giam_toi_da: null }, tien)).toBe('7,5%')
    expect(moTaMucGiam({ loai_giam: 'so_tien', gia_tri: '20000.00', giam_toi_da: null }, tien)).toBe('20000đ')
  })
})
