import { describe, expect, it } from 'vitest'
import { laLoiApi, loiTheoTruong } from './loi'

describe('laLoiApi', () => {
  it('nhận đúng định dạng {ma_loi, thong_diep, chi_tiet}', () => {
    expect(laLoiApi({ ma_loi: 'OTP_SAI', thong_diep: 'Sai', chi_tiet: { so_lan_con_lai: 2 } })).toBe(true)
    expect(laLoiApi({ ma_loi: 'X', thong_diep: 'y', chi_tiet: null })).toBe(true)
  })

  it.each([null, undefined, 'lỗi', 42, {}, { ma_loi: 1, thong_diep: 'x' }, { ma_loi: 'X' }])('từ chối %j', (v) => {
    expect(laLoiApi(v)).toBe(false)
  })
})

describe('loiTheoTruong', () => {
  it('gom danh sách {truong, loi} của lỗi validate thành bảng theo trường', () => {
    const loi = {
      ma_loi: 'DU_LIEU_KHONG_HOP_LE',
      thong_diep: 'Dữ liệu không hợp lệ',
      chi_tiet: [
        { truong: 'email', loi: 'Email không hợp lệ' },
        { truong: 'mat_khau', loi: 'Quá ngắn' },
      ],
    }
    expect(loiTheoTruong(loi)).toEqual({ email: 'Email không hợp lệ', mat_khau: 'Quá ngắn' })
  })

  it('hiểu lỗi trùng dữ liệu {truong: "email"}', () => {
    const loi = { ma_loi: 'TRUNG_DU_LIEU', thong_diep: 'Đã dùng', chi_tiet: { truong: 'email' } }
    expect(loiTheoTruong(loi)).toEqual({ email: 'Đã dùng' })
  })

  it('lỗi không có chi tiết theo trường thì trả bảng rỗng', () => {
    expect(loiTheoTruong({ ma_loi: 'OTP_SAI', thong_diep: 'x', chi_tiet: { so_lan_con_lai: 1 } })).toEqual({})
    expect(loiTheoTruong({ ma_loi: 'X', thong_diep: 'x', chi_tiet: null })).toEqual({})
  })
})
