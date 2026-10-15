import { describe, expect, it } from 'vitest'
import { matKhauDuManh } from './matKhau'

describe('matKhauDuManh (khớp backend mat_khau_du_manh)', () => {
  it.each(['abc12345', 'Mậtkhẩu123', 'a1b2c3d4', '        1a'])('%s đủ mạnh', (m) => {
    expect(matKhauDuManh(m)).toBe(true)
  })

  it.each(['abc1234', 'abcdefgh', '12345678', ''])('%s không đủ mạnh', (m) => {
    expect(matKhauDuManh(m)).toBe(false)
  })

  it('đếm ký tự Unicode chứ không đếm byte: 7 ký tự có dấu vẫn là 7', () => {
    expect(matKhauDuManh('Mậtkh1')).toBe(false)
  })
})
