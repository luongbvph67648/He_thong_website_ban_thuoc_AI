import { beforeEach, describe, expect, it } from 'vitest'
import { docGioCucBo, SO_LUONG_TOI_DA, themVaoDanhSach, useGioCucBo } from './gioHang'

beforeEach(() => {
  localStorage.clear()
  useGioCucBo.setState({ dong: [] })
})

describe('giỏ localStorage của khách vãng lai', () => {
  it('cộng dồn dòng cùng sản phẩm và đơn vị, cắt ở mức tối đa mỗi dòng', () => {
    const a = themVaoDanhSach([], { san_pham_id: 1, don_vi_id: 2, so_luong: 3 })
    const b = themVaoDanhSach(a, { san_pham_id: 1, don_vi_id: 2, so_luong: SO_LUONG_TOI_DA })
    expect(b).toEqual([{ san_pham_id: 1, don_vi_id: 2, so_luong: SO_LUONG_TOI_DA }])
    expect(themVaoDanhSach(b, { san_pham_id: 1, don_vi_id: 3, so_luong: 1 })).toHaveLength(2)
  })

  it('lưu xuống localStorage, đổi đơn vị gộp vào dòng đã có, xóa và làm rỗng', () => {
    const s = useGioCucBo.getState()
    s.them({ san_pham_id: 1, don_vi_id: 2, so_luong: 3 })
    useGioCucBo.getState().them({ san_pham_id: 1, don_vi_id: 3, so_luong: 4 })
    expect(docGioCucBo()).toHaveLength(2)
    useGioCucBo.getState().doiDonVi(1, 2, 3)
    expect(docGioCucBo()).toEqual([{ san_pham_id: 1, don_vi_id: 3, so_luong: 7 }])
    useGioCucBo.getState().datSoLuong(1, 3, 9)
    expect(docGioCucBo()[0].so_luong).toBe(9)
    useGioCucBo.getState().xoa(1, 3)
    expect(docGioCucBo()).toEqual([])
    useGioCucBo.getState().them({ san_pham_id: 5, don_vi_id: 6, so_luong: 1 })
    useGioCucBo.getState().lamRong()
    expect(docGioCucBo()).toEqual([])
  })

  it('bỏ qua dữ liệu hỏng trong localStorage', () => {
    localStorage.setItem('gio_hang_khach', '{khong phai json')
    expect(docGioCucBo()).toEqual([])
    localStorage.setItem('gio_hang_khach', JSON.stringify([{ san_pham_id: 1, don_vi_id: 2, so_luong: 0 }, { san_pham_id: 'x' }, { san_pham_id: 1, don_vi_id: 2, so_luong: 2 }]))
    expect(docGioCucBo()).toEqual([{ san_pham_id: 1, don_vi_id: 2, so_luong: 2 }])
  })
})
