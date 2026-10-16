import { describe, expect, it } from 'vitest'
import { ANH_TOI_DA, DUNG_LUONG_ANH_TOI_DA, loiTepAnh } from './anh'

describe('loiTepAnh', () => {
  it('nhận jpeg, png, webp trong giới hạn 5 MB', () => {
    for (const type of ['image/jpeg', 'image/png', 'image/webp']) expect(loiTepAnh({ type, size: 1000 })).toBeNull()
    expect(loiTepAnh({ type: 'image/png', size: DUNG_LUONG_ANH_TOI_DA })).toBeNull()
  })

  it.each([
    ['gif', { type: 'image/gif', size: 10 }, /JPEG, PNG hoặc WebP/],
    ['svg (chứa được script)', { type: 'image/svg+xml', size: 10 }, /JPEG, PNG hoặc WebP/],
    ['không rõ loại', { type: '', size: 10 }, /JPEG, PNG hoặc WebP/],
    ['quá 5 MB một byte', { type: 'image/png', size: DUNG_LUONG_ANH_TOI_DA + 1 }, /tối đa 5 MB/],
    ['tệp rỗng', { type: 'image/png', size: 0 }, /rỗng/],
  ])('từ chối %s', (_ten, tep, mau) => {
    expect(loiTepAnh(tep)).toMatch(mau)
  })

  it('tối đa 20 ảnh khớp backend', () => {
    expect(ANH_TOI_DA).toBe(20)
  })
})
