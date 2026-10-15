import { describe, expect, it } from 'vitest'
import { duongTiepTheo } from './chuyenHuong'

describe('duongTiepTheo', () => {
  it.each(['/gio-hang', '/tai-khoan/don-hang/DH123', '/tim-kiem?q=para&trang=2', '/san-pham/paracetamol#mo-ta'])(
    'nhận đường dẫn nội bộ %s',
    (duong) => expect(duongTiepTheo(duong)).toBe(duong),
  )

  it.each([
    ['không có', null],
    ['rỗng', ''],
    ['URL tuyệt đối', 'https://trang-lua-dao.example/dang-nhap'],
    ['cùng giao thức', '//trang-lua-dao.example'],
    ['gạch chéo ngược', '/\\trang-lua-dao.example'],
    ['javascript', 'javascript:alert(1)'],
    ['không bắt đầu bằng /', 'gio-hang'],
    ['tab ẩn sau dấu /', '/\t/trang-lua-dao.example'],
    ['xuống dòng', '/gio-hang\nSet-Cookie: x=1'],
  ])('từ chối %s và về trang mặc định', (_ten, tham) => expect(duongTiepTheo(tham)).toBe('/'))

  it('không quay lại chính các trang đăng nhập/đăng ký/quên mật khẩu (tránh vòng lặp)', () => {
    for (const duong of ['/dang-nhap', '/dang-nhap?tiep=/gio-hang', '/dang-ky', '/quen-mat-khau']) {
      expect(duongTiepTheo(duong)).toBe('/')
    }
  })

  it('dùng đường dẫn mặc định do người gọi chỉ định', () => expect(duongTiepTheo(null, '/tai-khoan')).toBe('/tai-khoan'))
})
