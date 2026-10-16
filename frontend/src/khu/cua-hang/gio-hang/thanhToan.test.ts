import { describe, expect, it } from 'vitest'
import { canKhoaMoi, duDieuKien, type FormDat, giaThayDoi, khoaChoLanDat, thanDatHang } from './thanhToan'

const F: FormDat = { hinhThuc: 'giao_tan_noi', phuongThuc: 'cod', diaChiId: 4, maGiamGia: null, ghiChu: '  ' }

describe('thanDatHang', () => {
  it('giao tận nơi gửi địa chỉ; bỏ mã và ghi chú rỗng; không gửi dòng hàng hay id khách', () => {
    expect(thanDatHang(F)).toEqual({ hinh_thuc_nhan: 'giao_tan_noi', phuong_thuc_tt: 'cod', dia_chi_id: 4 })
    expect(thanDatHang({ ...F, maGiamGia: 'SALE10', ghiChu: ' gọi trước ' }, '9000.00')).toEqual({
      hinh_thuc_nhan: 'giao_tan_noi', phuong_thuc_tt: 'cod', dia_chi_id: 4, ma_giam_gia: 'SALE10', ghi_chu: 'gọi trước', tong_tien_ky_vong: '9000.00',
    })
  })
  it('nhận tại nhà thuốc không gửi địa chỉ dù đã chọn', () => {
    expect(thanDatHang({ ...F, hinhThuc: 'nhan_tai_nha_thuoc' })).not.toHaveProperty('dia_chi_id')
  })
})

describe('duDieuKien', () => {
  it('giao tận nơi phải có địa chỉ', () => {
    expect(duDieuKien(F)).toBe(true)
    expect(duDieuKien({ ...F, diaChiId: null })).toBe(false)
    expect(duDieuKien({ ...F, diaChiId: null, hinhThuc: 'nhan_tai_nha_thuoc' })).toBe(true)
  })
})

describe('khoaChoLanDat (Idempotency-Key)', () => {
  it('cùng nội dung thì giữ khóa, nội dung đổi thì khóa mới', () => {
    let n = 0
    const tao = () => `k${++n}`
    const a = khoaChoLanDat(null, 'x', tao)
    expect(khoaChoLanDat(a, 'x', tao)).toBe(a)
    expect(khoaChoLanDat(a, 'y', tao).khoa).toBe('k2')
  })
  it('lỗi mạng giữ khóa, phản hồi dứt khoát đổi khóa', () => {
    expect(canKhoaMoi(null)).toBe(false)
    expect(canKhoaMoi({ ma_loi: 'HET_HANG', thong_diep: 'x', chi_tiet: null })).toBe(true)
  })
})

describe('giaThayDoi', () => {
  it('lấy tổng tính lại từ GIA_DA_THAY_DOI, lỗi khác thì null', () => {
    const ct = { tam_tinh: '1.00', giam_gia: '0.00', phi_van_chuyen: '0.00', tong_tien: '1.00', dong: [] }
    expect(giaThayDoi({ ma_loi: 'GIA_DA_THAY_DOI', thong_diep: 'x', chi_tiet: ct })?.tong_tien).toBe('1.00')
    expect(giaThayDoi({ ma_loi: 'HET_HANG', thong_diep: 'x', chi_tiet: ct })).toBeNull()
    expect(giaThayDoi(null)).toBeNull()
  })
})
