import { describe, expect, it } from 'vitest'
import { coMotTrong, coQuyen, type QuyenCuaToi } from './quyen'

const quyen: QuyenCuaToi = {
  'order.view': 'chi_xem',
  'order.confirm': 'day_du',
}

describe('coQuyen', () => {
  it('mặc định yêu cầu mức đầy đủ: quyền chỉ xem không đủ để thao tác', () => {
    expect(coQuyen(quyen, 'order.confirm')).toBe(true)
    expect(coQuyen(quyen, 'order.view')).toBe(false)
    expect(coQuyen(quyen, 'order.view', 'day_du')).toBe(false)
  })

  it('mức xem nhận cả chỉ xem lẫn đầy đủ', () => {
    expect(coQuyen(quyen, 'order.view', 'xem')).toBe(true)
    expect(coQuyen(quyen, 'order.confirm', 'xem')).toBe(true)
  })

  it('không có mã quyền thì không qua, kể cả mức xem', () => {
    expect(coQuyen(quyen, 'audit.view')).toBe(false)
    expect(coQuyen(quyen, 'audit.view', 'xem')).toBe(false)
    expect(coQuyen({}, 'order.view', 'xem')).toBe(false)
  })

  it('không bị đánh lừa bởi khóa có sẵn trong Object.prototype', () => {
    expect(coQuyen({}, 'constructor', 'xem')).toBe(false)
    expect(coQuyen({}, 'toString')).toBe(false)
    expect(coQuyen({}, '__proto__', 'xem')).toBe(false)
  })
})

describe('coMotTrong', () => {
  it('qua nếu có ít nhất một mã trong danh sách', () => {
    expect(coMotTrong(quyen, ['audit.view', 'order.confirm'])).toBe(true)
    expect(coMotTrong(quyen, ['audit.view', 'order.view'])).toBe(false) // order.view mới chỉ xem
    expect(coMotTrong(quyen, ['audit.view', 'order.view'], 'xem')).toBe(true)
    expect(coMotTrong(quyen, [])).toBe(false)
  })
})
