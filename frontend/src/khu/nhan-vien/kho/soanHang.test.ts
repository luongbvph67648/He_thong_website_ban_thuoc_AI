import { describe, expect, it } from 'vitest'
import { dongXong, quetMa, tatCaXong, xacNhanTay, type DongSoan } from './soanHang'

const dong = (id: number, so_luong: number, ma_vach: string | null): DongSoan =>
  ({ ct_don_hang_id: id, so_luong, ma_vach, san_pham_id: id, ten_san_pham: 'A', ten_don_vi: 'viên', he_so: 1, phan_bo: [], goi_y: [] })

describe('quét mã vạch khi soạn hàng', () => {
  const ds = [dong(1, 2, '893001'), dong(2, 1, null)]
  it('quét đúng mã tăng đếm, đủ số lượng thì dòng xong', () => {
    let q = quetMa(ds, {}, '893001')
    expect(q).toEqual({ 1: 1 })
    q = quetMa(ds, q!, ' 893001 ')
    expect(q).toEqual({ 1: 2 })
    expect(dongXong(ds[0], q!)).toBe(true)
  })
  it('mã lạ, mã trống hoặc dòng đã đủ bị từ chối', () => {
    expect(quetMa(ds, {}, '999')).toBeNull()
    expect(quetMa(ds, {}, '   ')).toBeNull()
    expect(quetMa(ds, { 1: 2 }, '893001')).toBeNull()
  })
  it('dòng không có mã vạch phải xác nhận tay; đủ mọi dòng mới xong', () => {
    let q: Record<number, number> = { 1: 2 }
    expect(tatCaXong(ds, q)).toBe(false)
    q = xacNhanTay(ds[1], q)
    expect(tatCaXong(ds, q)).toBe(true)
    expect(tatCaXong([], {})).toBe(false)
  })
})
