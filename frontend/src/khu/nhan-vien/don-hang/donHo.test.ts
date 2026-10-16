import { describe, expect, it } from 'vitest'
import { tamTinh, themDong, type DongHo } from './donHo'

const A: DongHo = { san_pham_id: 1, don_vi_id: 10, ten: 'A', ten_don_vi: 'viên', gia: '1000.00', so_luong: 2 }

describe('dòng đơn hộ', () => {
  it('cùng sản phẩm và đơn vị thì cộng số lượng', () => {
    const ds = themDong(themDong([], A), { ...A, so_luong: 3 })
    expect(ds).toHaveLength(1)
    expect(ds[0].so_luong).toBe(5)
  })
  it('khác đơn vị là dòng riêng; tạm tính cộng thành tiền', () => {
    const ds = themDong([A], { ...A, don_vi_id: 11, gia: '20000.00', so_luong: 1 })
    expect(ds).toHaveLength(2)
    expect(tamTinh(ds)).toBe(22000)
  })
})
