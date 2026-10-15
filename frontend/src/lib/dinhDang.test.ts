import { describe, expect, it } from 'vitest'
import { dinhDangNgay, dinhDangTien } from './dinhDang'

const NBSP = ' '

describe('dinhDangTien', () => {
  it('định dạng số đồng nguyên theo kiểu Việt Nam, ký hiệu đ dính liền số', () => {
    expect(dinhDangTien('125000.00')).toBe(`125.000${NBSP}₫`)
    expect(dinhDangTien(125000)).toBe(`125.000${NBSP}₫`)
    expect(dinhDangTien('0')).toBe(`0${NBSP}₫`)
    expect(dinhDangTien('1234567.00')).toBe(`1.234.567${NBSP}₫`)
  })

  it('không mất độ chính xác với số rất lớn (API trả chuỗi, không qua float)', () => {
    expect(dinhDangTien('999999999999.00')).toBe(`999.999.999.999${NBSP}₫`)
    expect(dinhDangTien('9007199254740993.00')).toBe(`9.007.199.254.740.993${NBSP}₫`)
  })

  it('làm tròn half-up về đồng như backend, kể cả số âm (xa số 0)', () => {
    expect(dinhDangTien('0.50')).toBe(`1${NBSP}₫`)
    expect(dinhDangTien('2.49')).toBe(`2${NBSP}₫`)
    expect(dinhDangTien('2.5')).toBe(`3${NBSP}₫`)
    expect(dinhDangTien('-2.5')).toBe(`-3${NBSP}₫`)
    expect(dinhDangTien('-50000.00')).toBe(`-50.000${NBSP}₫`)
    expect(dinhDangTien('999.5')).toBe(`1.000${NBSP}₫`)
  })

  it('không hiện -0', () => {
    expect(dinhDangTien('-0.4')).toBe(`0${NBSP}₫`)
    expect(dinhDangTien('-0')).toBe(`0${NBSP}₫`)
  })

  it('giá trị thiếu hoặc không hợp lệ hiện dấu gạch, không hiện NaN', () => {
    for (const v of [null, undefined, '', 'abc', '12abc', 'NaN', 'Infinity', Number.NaN, Number.POSITIVE_INFINITY]) {
      expect(dinhDangTien(v as never)).toBe('—')
    }
  })
})

describe('dinhDangNgay (múi giờ Asia/Ho_Chi_Minh)', () => {
  it('đổi thời điểm UTC sang giờ Việt Nam, kể cả khi qua nửa đêm', () => {
    expect(dinhDangNgay('2026-10-15T17:30:00Z')).toBe('16/10/2026')
    expect(dinhDangNgay('2026-10-15T16:59:59Z')).toBe('15/10/2026')
    expect(dinhDangNgay('2026-10-15T17:30:00Z', 'gio')).toBe('00:30')
    expect(dinhDangNgay('2026-10-15T17:30:00Z', 'ngayGio')).toBe('16/10/2026 00:30')
  })

  it('hiểu cả chuỗi có offset và đối tượng Date', () => {
    expect(dinhDangNgay('2026-10-16T00:30:00+07:00', 'ngayGio')).toBe('16/10/2026 00:30')
    expect(dinhDangNgay(new Date('2026-01-01T00:00:00Z'), 'ngayGio')).toBe('01/01/2026 07:00')
  })

  it('ngày thuần (hạn sử dụng) không bị dịch múi giờ', () => {
    expect(dinhDangNgay('2026-12-31')).toBe('31/12/2026')
    expect(dinhDangNgay('2026-01-01')).toBe('01/01/2026')
    expect(dinhDangNgay('2026-12-31', 'gio')).toBe('—') // ngày thuần không có giờ
    expect(dinhDangNgay('2026-12-31', 'ngayGio')).toBe('31/12/2026')
  })

  it('giá trị thiếu hoặc không hợp lệ hiện dấu gạch', () => {
    for (const v of [null, undefined, '', 'không phải ngày', '2026-13-45', '2026-02-30']) {
      expect(dinhDangNgay(v as never)).toBe('—')
    }
  })
})
