import { describe, expect, it } from 'vitest'
import { chuoiHoacNull, gonTen, loiDuongDan, loiTen, loiVanBan } from './duLieuChung'

describe('duLieuChung (cùng bảng ca với backend tests/san_pham/test_sp_du_lieu_chung.py)', () => {
  it('gonTen bỏ khoảng trắng đầu cuối và gộp khoảng trắng liên tiếp', () => {
    expect(gonTen('  Sanofi   Việt \t Nam ')).toBe('Sanofi Việt Nam')
    expect(gonTen('   ')).toBe('')
  })

  it('loiTen: bắt buộc, giới hạn độ dài sau khi gọn, không ký tự điều khiển', () => {
    expect(loiTen('Sanofi', 150)).toBeNull()
    expect(loiTen('   ', 150)).toBe('Vui lòng nhập tên')
    expect(loiTen('x'.repeat(150), 150)).toBeNull()
    expect(loiTen('x'.repeat(151), 150)).toBe('Tối đa 150 ký tự')
    expect(loiTen(`${'x'.repeat(100)}   ${'y'.repeat(49)}`, 150)).toBeNull() // gộp khoảng trắng: 150 ký tự
    expect(loiTen('Ok\u0000', 150)).toMatch(/ký tự điều khiển/)
    expect(loiTen('Ok\u0007', 150)).toMatch(/ký tự điều khiển/)
  })

  it('loiDuongDan: trống hợp lệ; chỉ nhận /... hoặc http(s)://... không khoảng trắng, tối đa 500', () => {
    for (const ok of ['', '   ', '/anh/a.png', 'https://cdn.example.com/a.png?x=1', 'http://localhost:9000/a', ` /a.png `, `/${'a'.repeat(499)}`]) {
      expect(loiDuongDan(ok), JSON.stringify(ok)).toBeNull()
    }
    for (const sai of [
      'javascript:alert(1)',
      'data:image/png;base64,AAAA',
      '//evil.example/a.png',
      '/a b.png',
      'ftp://x/y',
      'https://',
      `/${'a'.repeat(500)}`,
      '/a\u0000.png',
    ]) {
      expect(loiDuongDan(sai), JSON.stringify(sai)).toMatch(/Đường dẫn phải/)
    }
  })

  it('loiVanBan: tùy chọn, một dòng hay nhiều dòng', () => {
    expect(loiVanBan('', 100)).toBeNull()
    expect(loiVanBan('x'.repeat(100), 100)).toBeNull()
    expect(loiVanBan('x'.repeat(101), 100)).toBe('Tối đa 100 ký tự')
    expect(loiVanBan('a\nb', 100)).toBeNull() // một dòng: xuống dòng được gộp thành khoảng trắng
    expect(loiVanBan('a\nb', 100, true)).toBeNull()
    expect(loiVanBan('a\u0000b', 100, true)).toMatch(/ký tự điều khiển/)
    expect(loiVanBan('a\u0007b', 100, true)).toMatch(/ký tự điều khiển/)
  })

  it('chuoiHoacNull: trống là null, ngược lại đã gọn', () => {
    expect(chuoiHoacNull('  ')).toBeNull()
    expect(chuoiHoacNull(undefined)).toBeNull()
    expect(chuoiHoacNull('  Hoa   Kỳ ')).toBe('Hoa Kỳ')
    expect(chuoiHoacNull('  Dòng 1\n\nDòng 2 ', true)).toBe('Dòng 1\n\nDòng 2')
  })
})
