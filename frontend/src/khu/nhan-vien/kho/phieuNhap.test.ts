import { describe, expect, it } from 'vitest'
import { chonDonVi, tongTienPhieu, type SanPham } from './phieuNhap'

const SP: SanPham = {
  id: 1,
  sku: 'A',
  ten: 'A',
  don_vi_mac_dinh_id: 11,
  don_vi: [
    { id: 10, ten_don_vi: 'viên', he_so: 1, ma_vach: null },
    { id: 11, ten_don_vi: 'hộp', he_so: 100, ma_vach: '893' },
    { id: 12, ten_don_vi: 'thùng', he_so: 1000, ma_vach: '894' },
  ],
}

describe('phieuNhap', () => {
  it('chọn đơn vị theo mã vạch vừa quét, không khớp thì đơn vị mặc định', () => {
    expect(chonDonVi(SP, '894')).toBe(12)
    expect(chonDonVi(SP, 'ten sp')).toBe(11)
    expect(chonDonVi({ ...SP, don_vi_mac_dinh_id: null }, 'x')).toBe(10)
  })
  it('tổng tiền bỏ qua dòng chưa nhập', () => {
    expect(tongTienPhieu([{ soLuong: 2, giaNhap: 60000 }, { soLuong: null, giaNhap: 5 }, { soLuong: 3, giaNhap: null }])).toBe(120000)
  })
})
