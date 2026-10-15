import { describe, expect, it } from 'vitest'
import { phienTuNhanVien, type NhanVienToi } from './hoSoNoiBo'

const NV: NhanVienToi = {
  id: 9,
  ma_nhan_vien: 'NV0009',
  ho_ten: 'Lê Thị Mai',
  email: 'mai@example.com',
  so_dien_thoai: '0912345678',
  vai_tro: { ma: 'PHARMACIST', ten: 'Dược sĩ bán hàng' },
  phai_doi_mat_khau: true,
  quyen: { 'order.view': 'day_du', 'stock.view': 'chi_xem' },
}

describe('phienTuNhanVien', () => {
  it('đổi hồ sơ API sang dạng lưu trong store, giữ nguyên quyền và cờ đổi mật khẩu', () => {
    expect(phienTuNhanVien(NV)).toEqual({
      hoSo: {
        id: 9,
        hoTen: 'Lê Thị Mai',
        vaiTro: 'PHARMACIST',
        maNhanVien: 'NV0009',
        email: 'mai@example.com',
        soDienThoai: '0912345678',
      },
      quyen: { 'order.view': 'day_du', 'stock.view': 'chi_xem' },
      phaiDoiMatKhau: true,
    })
  })
})
