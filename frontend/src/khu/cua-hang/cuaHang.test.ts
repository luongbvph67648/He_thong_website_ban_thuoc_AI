import { describe, expect, it } from 'vitest'
import { capNhatThamSo, diemTrungBinh, docBoLoc, soBoLocDangDung, taoQuerySanPham } from './cuaHang'

const tham = (q: string) => new URLSearchParams(q)

describe('docBoLoc', () => {
  it('URL rỗng: mặc định', () => {
    expect(docBoLoc(tham(''))).toEqual({
      loai: undefined,
      thuongHieu: [],
      giaTu: undefined,
      giaDen: undefined,
      doiTuong: undefined,
      conHang: false,
      sapXep: 'moi',
      trang: 1,
    })
  })

  it('đọc đủ các bộ lọc', () => {
    const b = docBoLoc(tham('loai=thuc_pham_chuc_nang&thuong_hieu=3&thuong_hieu=5&gia_tu=0&gia_den=200000&doi_tuong=Trẻ em&con_hang=1&sap_xep=gia_tang&trang=4'))
    expect(b).toEqual({
      loai: 'thuc_pham_chuc_nang',
      thuongHieu: [3, 5],
      giaTu: 0,
      giaDen: 200000,
      doiTuong: 'Trẻ em',
      conHang: true,
      sapXep: 'gia_tang',
      trang: 4,
    })
  })

  it.each([
    ['loai=hack', { loai: undefined }],
    ['thuong_hieu=abc&thuong_hieu=-1&thuong_hieu=0&thuong_hieu=1.5&thuong_hieu=99999999999', { thuongHieu: [] }],
    ['thuong_hieu=2&thuong_hieu=2', { thuongHieu: [2] }],
    ['gia_tu=-5', { giaTu: undefined }],
    ['gia_tu=1.5&gia_den=abc', { giaTu: undefined, giaDen: undefined }],
    ['gia_den=10000000000000', { giaDen: undefined }],
    ['con_hang=true', { conHang: false }],
    ['sap_xep=ban_chay;drop', { sapXep: 'moi' }],
    ['trang=0', { trang: 1 }],
    ['trang=-3', { trang: 1 }],
    ['trang=x', { trang: 1 }],
    ['trang=99999999', { trang: 1 }],
    ['doi_tuong=%20%20', { doiTuong: undefined }],
  ])('giá trị lạ %s bị bỏ qua', (q, mong) => {
    expect(docBoLoc(tham(q))).toMatchObject(mong)
  })

  it('tối đa 20 thương hiệu và cắt đối tượng ở 100 ký tự', () => {
    const q = Array.from({ length: 30 }, (_, i) => `thuong_hieu=${i + 1}`).join('&') + `&doi_tuong=${'a'.repeat(200)}`
    const b = docBoLoc(tham(q))
    expect(b.thuongHieu).toHaveLength(20)
    expect(b.doiTuong).toHaveLength(100)
  })
})

describe('taoQuerySanPham', () => {
  it('mặc định chỉ gửi sắp xếp, trang, kích thước', () => {
    expect(taoQuerySanPham(docBoLoc(tham('')))).toEqual({
      danh_muc: undefined,
      loai: undefined,
      thuong_hieu_id: undefined,
      gia_tu: undefined,
      gia_den: undefined,
      doi_tuong: undefined,
      con_hang: undefined,
      sap_xep: 'moi',
      trang: 1,
      kich_thuoc: 12,
    })
  })

  it('đủ bộ lọc kèm slug danh mục', () => {
    const q = taoQuerySanPham(docBoLoc(tham('thuong_hieu=1&thuong_hieu=2&gia_tu=10&gia_den=20&con_hang=1&trang=2')), 'thuoc')
    expect(q).toMatchObject({ danh_muc: 'thuoc', thuong_hieu_id: [1, 2], gia_tu: 10, gia_den: 20, con_hang: true, trang: 2 })
  })

  it('giá từ lớn hơn giá đến thì đổi chỗ (không gửi yêu cầu chắc chắn bị 400)', () => {
    expect(taoQuerySanPham(docBoLoc(tham('gia_tu=500&gia_den=100')))).toMatchObject({ gia_tu: 100, gia_den: 500 })
  })
})

describe('capNhatThamSo', () => {
  it('đổi bộ lọc đưa về trang 1; giá trị mặc định không ghi lên URL', () => {
    const ra = capNhatThamSo(tham('trang=3&sap_xep=gia_tang'), { loai: 'duoc_my_pham' })
    expect(ra.toString()).toBe('loai=duoc_my_pham&sap_xep=gia_tang')
    expect(capNhatThamSo(ra, { sapXep: 'moi' }).toString()).toBe('loai=duoc_my_pham')
  })

  it('đổi trang giữ nguyên bộ lọc; trang 1 không ghi', () => {
    expect(capNhatThamSo(tham('loai=duoc_my_pham'), { trang: 2 }).toString()).toBe('loai=duoc_my_pham&trang=2')
    expect(capNhatThamSo(tham('loai=duoc_my_pham&trang=2'), { trang: 1 }).toString()).toBe('loai=duoc_my_pham')
  })

  it('thương hiệu nhiều giá trị và xóa bộ lọc', () => {
    const ra = capNhatThamSo(tham(''), { thuongHieu: [4, 7], giaTu: 0, giaDen: 90, conHang: true, doiTuong: 'Người lớn' })
    expect(ra.getAll('thuong_hieu')).toEqual(['4', '7'])
    expect(ra.get('gia_tu')).toBe('0')
    expect(capNhatThamSo(ra, { loai: undefined, thuongHieu: [], giaTu: undefined, giaDen: undefined, conHang: false, doiTuong: undefined }).toString()).toBe('')
  })

  it('bỏ giá trị sai có sẵn trên URL khi ghi lại', () => {
    expect(capNhatThamSo(tham('loai=hack&gia_tu=x'), { conHang: true }).toString()).toBe('con_hang=1')
  })
})

describe('soBoLocDangDung', () => {
  it('đếm nhóm bộ lọc, khoảng giá tính một, bỏ qua sắp xếp và trang', () => {
    expect(soBoLocDangDung(docBoLoc(tham('sap_xep=ten&trang=2')))).toBe(0)
    expect(soBoLocDangDung(docBoLoc(tham('loai=duoc_my_pham&thuong_hieu=1&thuong_hieu=2&gia_tu=1&gia_den=2&doi_tuong=a&con_hang=1')))).toBe(5)
  })
})

describe('diemTrungBinh', () => {
  it.each([
    [16, 5, '3,2'],
    [10, 2, '5,0'],
    [1, 3, '0,3'],
    [14, 3, '4,7'],
  ])('%i sao / %i đánh giá = %s', (tong, so, ra) => expect(diemTrungBinh(tong, so)).toBe(ra))

  it('chưa có đánh giá thì null (không chia cho 0)', () => {
    expect(diemTrungBinh(0, 0)).toBeNull()
  })
})
