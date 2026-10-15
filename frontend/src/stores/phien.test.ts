import { beforeEach, describe, expect, it } from 'vitest'
import { usePhien } from './phien'

const hoSo = { id: 7, hoTen: 'Nguyễn Thị Mai', vaiTro: 'PHARMACIST' }

describe('usePhien', () => {
  beforeEach(() => {
    localStorage.clear()
    usePhien.getState().dangXuat()
  })

  it('ban đầu chưa đăng nhập', () => {
    const p = usePhien.getState()
    expect(p.accessToken).toBeNull()
    expect(p.loai).toBeNull()
    expect(p.quyen).toEqual({})
  })

  it('đăng nhập nội bộ lưu token, hồ sơ và quyền', () => {
    usePhien.getState().dangNhap({ accessToken: 't1', loai: 'noi_bo', hoSo, quyen: { 'order.view': 'day_du' } })
    const p = usePhien.getState()
    expect([p.accessToken, p.loai, p.hoSo]).toEqual(['t1', 'noi_bo', hoSo])
    expect(p.quyen).toEqual({ 'order.view': 'day_du' })
  })

  it('làm mới token chỉ đổi token, giữ nguyên hồ sơ và quyền', () => {
    usePhien.getState().dangNhap({ accessToken: 't1', loai: 'noi_bo', hoSo, quyen: { 'order.view': 'day_du' } })
    usePhien.getState().datToken('t2')
    const p = usePhien.getState()
    expect(p.accessToken).toBe('t2')
    expect(p.hoSo).toEqual(hoSo)
    expect(p.quyen).toEqual({ 'order.view': 'day_du' })
  })

  it('đăng xuất xóa sạch phiên', () => {
    usePhien.getState().dangNhap({ accessToken: 't1', loai: 'khach', hoSo, quyen: {} })
    usePhien.getState().dangXuat()
    const p = usePhien.getState()
    expect([p.accessToken, p.loai, p.hoSo]).toEqual([null, null, null])
  })

  it('không ghi token hay hồ sơ vào localStorage/sessionStorage (token chỉ ở bộ nhớ)', () => {
    usePhien.getState().dangNhap({ accessToken: 'bi-mat', loai: 'noi_bo', hoSo, quyen: { 'order.view': 'day_du' } })
    const kho = JSON.stringify({ ...localStorage }) + JSON.stringify({ ...sessionStorage })
    expect(kho).not.toContain('bi-mat')
    expect(kho).not.toContain('Nguyễn')
    expect(kho).not.toContain('order.view')
    expect(sessionStorage.length).toBe(0)
    // Ngoại lệ duy nhất: gợi ý loại phiên để biết có nên thử lấy lại phiên khi tải trang.
    expect({ ...localStorage }).toEqual({ phien_goi_y: 'noi_bo' })
  })

  it('đăng nhập mặc định không bị bắt đổi mật khẩu; truyền cờ thì lưu và đăng xuất xóa', () => {
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo, quyen: {} })
    expect(usePhien.getState().phaiDoiMatKhau).toBe(false)
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo, quyen: {}, phaiDoiMatKhau: true })
    expect(usePhien.getState().phaiDoiMatKhau).toBe(true)
    usePhien.getState().dangXuat()
    expect(usePhien.getState().phaiDoiMatKhau).toBe(false)
  })

  it('cập nhật hồ sơ chỉ đổi trường được truyền, giữ token và quyền; chưa đăng nhập thì không làm gì', () => {
    usePhien.getState().capNhatHoSo({ hoTen: 'X' })
    expect(usePhien.getState().hoSo).toBeNull()
    usePhien.getState().dangNhap({ accessToken: 't1', loai: 'noi_bo', hoSo, quyen: { 'order.view': 'day_du' } })
    usePhien.getState().capNhatHoSo({ hoTen: 'Tên mới' })
    const p = usePhien.getState()
    expect(p.hoSo).toEqual({ ...hoSo, hoTen: 'Tên mới' })
    expect([p.accessToken, p.quyen]).toEqual(['t1', { 'order.view': 'day_du' }])
  })

  it('đăng xuất xóa gợi ý phiên', () => {
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'khach', hoSo, quyen: {} })
    expect(localStorage.getItem('phien_goi_y')).toBe('khach')
    usePhien.getState().dangXuat()
    expect(localStorage.length).toBe(0)
  })
})
