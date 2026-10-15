import { describe, expect, it } from 'vitest'
import { nhanMuc, thanCapNhatQuyen, tinhThayDoiQuyen } from './quyenVaiTro'

describe('tinhThayDoiQuyen', () => {
  it('liệt kê gán mới, gỡ, đổi mức; bỏ qua mã không đổi; sắp theo mã', () => {
    const truoc = { 'order.view': 'day_du', 'stock.view': 'chi_xem', 'pos.sell': 'day_du', 'profile.self': 'day_du' } as const
    const sau = { 'order.view': 'day_du', 'stock.view': 'day_du', 'pos.sell': null, 'stock.import': 'chi_xem', 'profile.self': 'day_du' } as const
    expect(tinhThayDoiQuyen(truoc, sau)).toEqual([
      { ma: 'pos.sell', tu: 'day_du', den: null },
      { ma: 'stock.import', tu: null, den: 'chi_xem' },
      { ma: 'stock.view', tu: 'chi_xem', den: 'day_du' },
    ])
  })

  it('không có thay đổi thì rỗng; thiếu khóa coi như null', () => {
    expect(tinhThayDoiQuyen({ a: 'day_du', b: null }, { a: 'day_du' })).toEqual([])
    expect(tinhThayDoiQuyen({}, { a: null })).toEqual([])
  })
})

describe('thanCapNhatQuyen', () => {
  it('chỉ giữ mã có quyền', () => {
    expect(thanCapNhatQuyen({ a: 'day_du', b: null, c: 'chi_xem' })).toEqual({ a: 'day_du', c: 'chi_xem' })
  })
})

describe('nhanMuc', () => {
  it.each([
    ['day_du', 'Đầy đủ'],
    ['chi_xem', 'Chỉ xem'],
    [null, 'Không có'],
  ] as const)('%s -> %s', (muc, nhan) => expect(nhanMuc(muc)).toBe(nhan))
})
