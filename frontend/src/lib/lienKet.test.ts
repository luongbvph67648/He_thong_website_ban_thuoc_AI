import { describe, expect, it } from 'vitest'
import { laLienKetNgoai, lienKetAnToan } from './lienKet'

describe('lienKetAnToan', () => {
  it.each([
    ['/danh-muc/thuoc', '/danh-muc/thuoc'],
    ['/san-pham/abc?x=1#y', '/san-pham/abc?x=1#y'],
    ['https://example.com/a.pdf', 'https://example.com/a.pdf'],
    ['http://example.com', 'http://example.com'],
    ['HTTPS://EXAMPLE.COM', 'HTTPS://EXAMPLE.COM'],
  ])('%s hợp lệ', (vao, ra) => expect(lienKetAnToan(vao)).toBe(ra))

  it.each([
    'javascript:alert(1)',
    'JaVaScRiPt:alert(1)',
    'data:text/html,<script>1</script>',
    '//evil.example/x',
    '/\\evil.example',
    'ftp://example.com',
    'vbscript:x',
    'abc',
    '',
    ' /danh-muc',
    '/danh muc',
    '/a\nb',
    'https://',
    'https:///x',
  ])('%j bị từ chối', (vao) => expect(lienKetAnToan(vao)).toBeNull())

  it('null và undefined', () => {
    expect(lienKetAnToan(null)).toBeNull()
    expect(lienKetAnToan(undefined)).toBeNull()
  })

  it('laLienKetNgoai', () => {
    expect(laLienKetNgoai('https://a.b')).toBe(true)
    expect(laLienKetNgoai('/a')).toBe(false)
  })
})
