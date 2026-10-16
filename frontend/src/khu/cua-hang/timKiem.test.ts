import { describe, expect, it } from 'vitest'
import { chuanHoaTuKhoa, duDieuKienTim, duongDanGoiY, duongDanTimKiem } from './timKiem'

describe('chuanHoaTuKhoa', () => {
  it.each([
    ['  Para   cetamol \n 500\t', 'Para cetamol 500'],
    ['', ''],
    ['   ', ''],
  ])('%j -> %j', (vao, ra) => expect(chuanHoaTuKhoa(vao)).toBe(ra))

  it('null, undefined và cắt 100 ký tự', () => {
    expect(chuanHoaTuKhoa(null)).toBe('')
    expect(chuanHoaTuKhoa(undefined)).toBe('')
    expect(chuanHoaTuKhoa('a'.repeat(250))).toHaveLength(100)
    expect(chuanHoaTuKhoa('a'.repeat(99) + ' ' + 'b'.repeat(10))).toBe('a'.repeat(99)) // không để lại khoảng trắng cuối
  })
})

describe('duDieuKienTim', () => {
  it('cần ít nhất 2 ký tự sau khi chuẩn hóa', () => {
    expect(duDieuKienTim('p')).toBe(false)
    expect(duDieuKienTim('  p  ')).toBe(false)
    expect(duDieuKienTim('pa')).toBe(true)
    expect(duDieuKienTim('')).toBe(false)
  })
})

describe('đường dẫn', () => {
  it('mã hóa ký tự đặc biệt trong từ khóa', () => {
    expect(duongDanTimKiem('  bo phe ')).toBe('/tim-kiem?q=bo%20phe')
    expect(duongDanTimKiem('a&b=c#d%')).toBe('/tim-kiem?q=a%26b%3Dc%23d%25')
  })

  it('gợi ý sản phẩm mở chi tiết, hoạt chất chạy tìm kiếm', () => {
    const sp = { kieu: 'san_pham', ten: 'Paracetamol 500mg', slug: 'paracetamol-500mg', loai_san_pham: 'thuoc_khong_ke_don', can_tu_van: false } as const
    expect(duongDanGoiY(sp)).toBe('/san-pham/paracetamol-500mg?nguon=tim_kiem')
    const hc = { kieu: 'hoat_chat', ten: 'Paracetamol', slug: null, loai_san_pham: null, can_tu_van: false } as const
    expect(duongDanGoiY(hc)).toBe('/tim-kiem?q=Paracetamol')
    expect(duongDanGoiY({ ...sp, slug: null })).toBe('/tim-kiem?q=Paracetamol%20500mg') // thiếu slug: không dựng liên kết hỏng
  })
})
