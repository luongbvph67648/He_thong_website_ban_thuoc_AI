import { describe, expect, it } from 'vitest'
import type { components } from '../api/schema'
import { bangNhau, kiemTraGiaTri, loiTheoTruongCauHinh, nhomTheoChuDe } from './cauHinh'

type Muc = components['schemas']['CauHinhDoc']

const co = (tuyChon: Partial<Muc>): Muc => ({
  khoa: 'k',
  nhom: 'N',
  nhan: 'Nhãn',
  mo_ta: null,
  kieu: 'so',
  don_vi: 'ngày',
  toi_thieu: 1,
  toi_da: 730,
  truong: [],
  gia_tri: 90,
  phien_ban: 'a'.repeat(16),
  nhan_vien_cap_nhat: null,
  updated_at: null,
  ...tuyChon,
})
const NHOM_OTP = co({
  kieu: 'nhom_so',
  don_vi: null,
  toi_thieu: null,
  toi_da: null,
  truong: [
    { ten: 'moi_sdt_moi_gio', nhan: 'Mỗi số', don_vi: 'lần', toi_thieu: 1, toi_da: 20 },
    { ten: 'moi_ip_moi_gio', nhan: 'Mỗi IP', don_vi: 'lần', toi_thieu: 1, toi_da: 200 },
  ],
  gia_tri: { moi_sdt_moi_gio: 5, moi_ip_moi_gio: 20 },
})
const GIO = co({ kieu: 'gio_lam_viec', don_vi: null, toi_thieu: null, toi_da: null, gia_tri: { bat_dau: '08:00', ket_thuc: '21:00', ngay_trong_tuan: [1, 2, 3] } })

describe('kiemTraGiaTri: số nguyên và tiền', () => {
  it.each([1, 90, 730])('nhận %s', (v) => expect(kiemTraGiaTri(co({}), v)).toEqual({}))
  it.each([0, 731, -1, 90.5, null, undefined, '90', true, Number.NaN, Number.POSITIVE_INFINITY, 1e30])('từ chối %s kèm khoảng cho phép', (v) => {
    const loi = kiemTraGiaTri(co({}), v)
    expect(Object.keys(loi)).toEqual(['gia_tri'])
    expect(loi.gia_tri).toMatch(/từ 1 đến 730 ngày/)
  })
  it('tiền hiện khoảng có dấu chấm ngăn nghìn', () => {
    expect(kiemTraGiaTri(co({ kieu: 'tien', don_vi: 'đồng', toi_thieu: 0, toi_da: 1_000_000 }), 2_000_000).gia_tri).toMatch(/từ 0 đến 1\.000\.000 đồng/)
  })
})

describe('kiemTraGiaTri: nhóm số', () => {
  it('hợp lệ', () => expect(kiemTraGiaTri(NHOM_OTP, { moi_sdt_moi_gio: 3, moi_ip_moi_gio: 50 })).toEqual({}))
  it('báo lỗi theo từng trường, trường đúng không bị báo', () => {
    const loi = kiemTraGiaTri(NHOM_OTP, { moi_sdt_moi_gio: 0, moi_ip_moi_gio: 50 })
    expect(Object.keys(loi)).toEqual(['moi_sdt_moi_gio'])
  })
  it('thiếu trường và sai kiểu', () => {
    expect(Object.keys(kiemTraGiaTri(NHOM_OTP, { moi_sdt_moi_gio: 3 }))).toEqual(['moi_ip_moi_gio'])
    expect(Object.keys(kiemTraGiaTri(NHOM_OTP, 5))).toEqual(['gia_tri'])
    expect(Object.keys(kiemTraGiaTri(NHOM_OTP, null))).toEqual(['gia_tri'])
  })
})

describe('kiemTraGiaTri: giờ làm việc', () => {
  it('hợp lệ', () => expect(kiemTraGiaTri(GIO, { bat_dau: '00:00', ket_thuc: '23:59', ngay_trong_tuan: [7] })).toEqual({}))
  it.each(['8:00', '24:00', '08:60', '', '08:00:00', '٠٨:٠٠', '0٨:00'])('giờ sai "%s"', (g) => {
    expect(kiemTraGiaTri(GIO, { bat_dau: g, ket_thuc: '21:00', ngay_trong_tuan: [1] })).toHaveProperty('bat_dau')
  })
  it('bắt đầu phải trước kết thúc', () => {
    expect(kiemTraGiaTri(GIO, { bat_dau: '21:00', ket_thuc: '08:00', ngay_trong_tuan: [1] })).toHaveProperty('ket_thuc')
    expect(kiemTraGiaTri(GIO, { bat_dau: '08:00', ket_thuc: '08:00', ngay_trong_tuan: [1] })).toHaveProperty('ket_thuc')
  })
  it.each([[[]], [[0]], [[8]], [[1, 1]], [['1']], [null]])('ngày không hợp lệ %j', (ngay) => {
    expect(kiemTraGiaTri(GIO, { bat_dau: '08:00', ket_thuc: '21:00', ngay_trong_tuan: ngay })).toHaveProperty('ngay_trong_tuan')
  })
})

describe('bangNhau', () => {
  it('so sánh nội dung, không phụ thuộc thứ tự khóa; số khác chuỗi', () => {
    expect(bangNhau({ a: 1, b: [1, 2] }, { b: [1, 2], a: 1 })).toBe(true)
    expect(bangNhau({ a: 1 }, { a: '1' })).toBe(false)
    expect(bangNhau([1, 2], [2, 1])).toBe(false)
    expect(bangNhau(null, null)).toBe(true)
    expect(bangNhau(null, 0)).toBe(false)
  })
})

describe('loiTheoTruongCauHinh', () => {
  it('gom lỗi máy chủ theo trường (bỏ tiền tố gia_tri.), lỗi chung vào khóa gia_tri', () => {
    expect(loiTheoTruongCauHinh([{ truong: 'gia_tri.moi_ip_moi_gio', loi: 'Thiếu trường này' }, { truong: 'gia_tri', loi: 'Sai' }])).toEqual({ moi_ip_moi_gio: 'Thiếu trường này', gia_tri: 'Sai' })
    expect(loiTheoTruongCauHinh(null)).toEqual({})
    expect(loiTheoTruongCauHinh('x')).toEqual({})
  })
})

describe("nhomTheoChuDe", () => {
  it('giữ thứ tự xuất hiện của nhóm và của khóa trong nhóm', () => {
    const ds = [co({ khoa: 'a', nhom: 'X' }), co({ khoa: 'b', nhom: 'Y' }), co({ khoa: 'c', nhom: 'X' })]
    expect(nhomTheoChuDe(ds).map(([nhom, muc]) => [nhom, muc.map((m) => m.khoa)])).toEqual([['X', ['a', 'c']], ['Y', ['b']]])
  })
})
