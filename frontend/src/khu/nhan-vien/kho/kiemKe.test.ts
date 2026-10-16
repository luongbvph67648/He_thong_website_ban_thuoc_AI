import { describe, expect, it } from 'vitest'
import type { components } from '../../../api/schema'
import { chenhLech, locDong } from './kiemKe'

type Dong = components['schemas']['DongKiemKe']
const d = (lo_id: number, ten: string, so_lo: string, ss: number, tt: number | null): Dong => ({
  lo_id, san_pham: { id: lo_id, sku: `SKU${lo_id}`, ten }, so_lo, han_su_dung: '2027-01-01', so_luong_so_sach: ss, so_luong_thuc_te: tt, chenh_lech: tt === null ? null : tt - ss,
})
const DONG = [d(1, 'Paracetamol', 'L01', 10, 8), d(2, 'Vitamin C', 'L02', 5, 5), d(3, 'Paracetamol', 'L03', 4, null)]

describe('kiemKe', () => {
  it('chênh lệch = thực tế - sổ sách, null khi chưa nhập', () => {
    expect(chenhLech(10, 8)).toBe(-2)
    expect(chenhLech(10, 0)).toBe(-10)
    expect(chenhLech(10, null)).toBeNull()
  })
  it('lọc theo từ khóa và chỉ dòng lệch, tính cả số đang gõ', () => {
    expect(locDong(DONG, 'para', false).map((x) => x.lo_id)).toEqual([1, 3])
    expect(locDong(DONG, 'l02', false).map((x) => x.lo_id)).toEqual([2])
    expect(locDong(DONG, '', true).map((x) => x.lo_id)).toEqual([1])
    expect(locDong(DONG, '', true, { 2: 3, 1: 10 }).map((x) => x.lo_id)).toEqual([2])
  })
})
