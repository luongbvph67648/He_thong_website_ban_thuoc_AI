import { describe, expect, it } from 'vitest'
import { dongTuSanPham, themDongPos, tongPos, type DongPos, type SanPhamPos } from './pos'

const SP = (rieng: Partial<SanPhamPos> = {}): SanPhamPos => ({
  id: 1, ten: 'Panadol', loai_san_pham: 'thuoc_khong_ke_don', don_vi_co_so: 'viên', ton_quay: 50, co_lo_can_han: false, hoat_chat: [],
  don_vi: [
    { id: 10, ten_don_vi: 'viên', he_so: 1, gia_ban: '1000.00', ma_vach: null },
    { id: 11, ten_don_vi: 'hộp', he_so: 10, gia_ban: '9000.00', ma_vach: '893' },
  ],
  ...rieng,
})
const DONG = (rieng: Partial<DongPos> = {}): DongPos => ({ san_pham_id: 1, don_vi_id: 10, so_luong: 1, ten: 'Panadol', ten_don_vi: 'viên', gia: '1000.00', ke_don: false, ...rieng })

describe('giỏ POS', () => {
  it('cộng dồn cùng sản phẩm và đơn vị, tách đơn vị khác nhau', () => {
    let ds = themDongPos([], DONG())
    ds = themDongPos(ds, DONG({ so_luong: 2 }))
    ds = themDongPos(ds, DONG({ don_vi_id: 11, ten_don_vi: 'hộp', gia: '9000.00' }))
    expect(ds.map((d) => [d.don_vi_id, d.so_luong])).toEqual([[10, 3], [11, 1]])
    expect(tongPos(ds)).toBe(12000)
  })

  it('quét mã vạch chọn đúng đơn vị khớp; mặc định là đơn vị nhỏ nhất (bán lẻ theo viên)', () => {
    expect(dongTuSanPham(SP({ don_vi_khop_ma_vach: 11 }))!.don_vi_id).toBe(11)
    expect(dongTuSanPham(SP())!.ten_don_vi).toBe('viên')
    expect(dongTuSanPham(SP(), 11, 3)).toMatchObject({ don_vi_id: 11, so_luong: 3 })
    expect(dongTuSanPham(SP({ don_vi: [] }))).toBeNull()
  })

  it('đánh dấu thuốc kê đơn', () => {
    expect(dongTuSanPham(SP({ loai_san_pham: 'thuoc_ke_don' }))!.ke_don).toBe(true)
  })
})
