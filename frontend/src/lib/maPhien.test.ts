import { afterEach, describe, expect, it, vi } from 'vitest'
import { layMaPhien, MAU_MA_PHIEN } from './maPhien'

afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('layMaPhien', () => {
  it('sinh mã đúng mẫu backend và giữ nguyên ở các lần sau', () => {
    const a = layMaPhien()
    expect(a).toMatch(MAU_MA_PHIEN)
    expect(a).toHaveLength(22)
    expect(layMaPhien()).toBe(a)
    expect(localStorage.getItem('ma_phien_khach')).toBe(a)
  })

  it('mã khác nhau giữa các trình duyệt', () => {
    const a = layMaPhien()
    localStorage.clear()
    expect(layMaPhien()).not.toBe(a)
  })

  it('mã đã lưu bị sửa sai định dạng thì sinh lại', () => {
    localStorage.setItem('ma_phien_khach', 'có dấu cách <script>')
    expect(layMaPhien()).toMatch(MAU_MA_PHIEN)
  })

  it('không đọc/ghi được localStorage vẫn trả mã (không ném lỗi)', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('chặn')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('chặn')
    })
    expect(layMaPhien()).toMatch(MAU_MA_PHIEN)
  })

  it('không có crypto thì null', () => {
    vi.stubGlobal('crypto', undefined)
    expect(layMaPhien()).toBeNull()
    vi.unstubAllGlobals()
  })
})
