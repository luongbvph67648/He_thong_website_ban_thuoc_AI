import { describe, expect, it } from 'vitest'
import { kiemTraDong, tonKhu } from './phieuKho'

describe('tonKhu', () => {
  const lo = { so_luong_ton: 10, so_luong_giu: 3, so_luong_biet_tru: 4 }
  it('khu bán trừ hàng đang giữ, biệt trữ lấy nguyên', () => {
    expect(tonKhu(lo, 'kho_ban')).toBe(7)
    expect(tonKhu(lo, 'biet_tru')).toBe(4)
  })
  it('thiếu số liệu coi là 0', () => {
    expect(tonKhu({ so_luong_ton: null, so_luong_giu: null, so_luong_biet_tru: null }, 'kho_ban')).toBe(0)
  })
})

describe('kiemTraDong', () => {
  it('bắt dòng trống, thiếu lô, số lượng sai, trùng', () => {
    expect(kiemTraDong([])).toMatch(/ít nhất/)
    expect(kiemTraDong([{ lo_id: null, tu_khu: 'kho_ban', so_luong: 1 }])).toMatch(/chưa chọn lô/)
    expect(kiemTraDong([{ lo_id: 1, tu_khu: 'kho_ban', so_luong: 0 }])).toMatch(/số lượng/)
    expect(kiemTraDong([{ lo_id: 1, tu_khu: 'kho_ban', so_luong: 1.5 }])).toMatch(/số lượng/)
    expect(kiemTraDong([{ lo_id: 1, tu_khu: 'kho_ban', so_luong: 1 }, { lo_id: 1, tu_khu: 'kho_ban', so_luong: 2 }])).toMatch(/trùng/)
  })
  it('cùng lô khác khu là hợp lệ', () => {
    expect(kiemTraDong([{ lo_id: 1, tu_khu: 'kho_ban', so_luong: 1 }, { lo_id: 1, tu_khu: 'biet_tru', so_luong: 2 }])).toBe('')
  })
})
