import { describe, expect, it } from 'vitest'
import { duongSauDangNhap, trangDauTienDuocPhep } from './dieuHuong'

describe('duongSauDangNhap', () => {
  it('Admin vào khu quản trị, dược sĩ và kho vào khu nhân viên', () => {
    expect(duongSauDangNhap('ADMIN')).toBe('/quan-tri')
    expect(duongSauDangNhap('PHARMACIST')).toBe('/nhan-vien')
    expect(duongSauDangNhap('WAREHOUSE')).toBe('/nhan-vien')
  })

  it('vai trò lạ hoặc thiếu đi vào khu nhân viên (backend vẫn kiểm quyền từng trang)', () => {
    expect(duongSauDangNhap(undefined)).toBe('/nhan-vien')
    expect(duongSauDangNhap('KHAC')).toBe('/nhan-vien')
  })
})

describe('trangDauTienDuocPhep', () => {
  const muc = [
    { duong: '/a', quyen: ['x.view'], nhan: 'A', chucNang: ['T1'] },
    { duong: '/b/:id', quyen: ['y.view'], nhan: 'B', chucNang: ['T2'], trongMenu: false },
    { duong: '/c', quyen: ['y.view'], nhan: 'C', chucNang: ['T3'] },
  ]

  it('chọn mục menu đầu tiên mà người dùng có quyền, bỏ qua trang chi tiết', () => {
    expect(trangDauTienDuocPhep(muc, { 'y.view': 'chi_xem' })).toBe('/c')
    expect(trangDauTienDuocPhep(muc, { 'x.view': 'day_du', 'y.view': 'day_du' })).toBe('/a')
  })

  it('không có quyền nào thì trả null', () => {
    expect(trangDauTienDuocPhep(muc, {})).toBeNull()
  })
})
