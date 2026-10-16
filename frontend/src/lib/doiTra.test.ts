import { describe, expect, it } from 'vitest'
import { loiTepBangChung } from './doiTra'

describe('loiTepBangChung', () => {
  const MB = 1024 * 1024
  it.each([
    ['a.jpg', 'image/jpeg', 5 * MB, null],
    ['a.jpg', 'image/jpeg', 5 * MB + 1, 'quá dung lượng'],
    ['v.mp4', 'video/mp4', 30 * MB, null],
    ['v.mp4', 'video/mp4', 30 * MB + 1, 'quá dung lượng'],
    ['a.gif', 'image/gif', 10, 'chỉ nhận'],
  ])('%s %s %d', (name, type, size, mong) => {
    const l = loiTepBangChung({ name, type, size })
    if (mong === null) expect(l).toBeNull()
    else expect(l).toContain(mong)
  })
})
