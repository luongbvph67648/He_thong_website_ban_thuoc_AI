import { describe, expect, it } from 'vitest'
import { chuanHoaSdt } from './dienThoai'

describe('chuanHoaSdt (khớp backend core/dien_thoai.py)', () => {
  it.each([
    ['0912345678', '0912345678'],
    ['0912 345 678', '0912345678'],
    ['0912.345.678', '0912345678'],
    ['0912-345-678', '0912345678'],
    ['+84912345678', '0912345678'],
    ['84912345678', '0912345678'],
    ['+84 912 345 678', '0912345678'],
    ['  0386123456  ', '0386123456'],
  ])('%s -> %s', (vao, ra) => {
    expect(chuanHoaSdt(vao)).toBe(ra)
  })

  it.each([
    '',
    '   ',
    '091234567',
    '09123456789',
    '0212345678',
    '0112345678',
    'abcdefghij',
    '09123x5678',
    '+849123456',
    '++84912345678',
    '٠٩١٢٣٤٥٦٧٨',
    '09١٢٣٤٥٦٧٨',
  ])('từ chối %s', (vao) => {
    expect(chuanHoaSdt(vao)).toBeNull()
  })
})
