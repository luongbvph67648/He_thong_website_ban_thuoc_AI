import { describe, expect, it } from 'vitest'
import { duocSiHuyDuoc, duocSiXacNhanDuoc, khachHuyDuoc } from './donHang'

describe('quyền thao tác theo trạng thái đơn', () => {
  it('khách hủy được trước khi soạn hàng, không hủy được sau đó', () => {
    for (const tt of ['cho_khach_xac_nhan', 'cho_thanh_toan', 'cho_xac_nhan', 'da_xac_nhan'] as const) expect(khachHuyDuoc(tt)).toBe(true)
    for (const tt of ['dang_soan_hang', 'cho_lay_hang', 'dang_giao', 'da_giao', 'hoan_tat', 'da_huy'] as const) expect(khachHuyDuoc(tt)).toBe(false)
  })
  it('dược sĩ chỉ xác nhận đơn chờ xác nhận', () => {
    expect(duocSiXacNhanDuoc('cho_xac_nhan')).toBe(true)
    expect(duocSiXacNhanDuoc('da_xac_nhan')).toBe(false)
  })
  it('dược sĩ hủy được đến khi hàng rời kho', () => {
    for (const tt of ['cho_xac_nhan', 'da_xac_nhan', 'dang_soan_hang', 'cho_lay_hang'] as const) expect(duocSiHuyDuoc(tt)).toBe(true)
    for (const tt of ['cho_thanh_toan', 'dang_giao', 'da_giao', 'da_huy'] as const) expect(duocSiHuyDuoc(tt)).toBe(false)
  })
})
