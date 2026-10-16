import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { WsGia } from '../test/wsGia'
import { urlChatWs, usePhongChat } from './phongChat'

beforeEach(() => {
  WsGia.tatCa = []
  vi.stubGlobal('WebSocket', WsGia)
})
afterEach(() => vi.unstubAllGlobals())

describe('phòng chat trực tiếp (KTV12/DS06)', () => {
  it('dựng URL ws/wss theo giao thức và không đưa token lên URL', () => {
    expect(urlChatWs('abc', { protocol: 'http:', host: 'localhost:5173' })).toBe('ws://localhost:5173/api/v1/tu-van/ws?ma_phien=abc')
    expect(urlChatWs('a b', { protocol: 'https:', host: 'x.vn' })).toBe('wss://x.vn/api/v1/tu-van/ws?ma_phien=a%20b')
  })

  it('chưa bật (maPhien null) thì không mở kết nối', () => {
    renderHook(() => usePhongChat({ maPhien: null, vaiTro: 'khach' }))
    expect(WsGia.tatCa).toHaveLength(0)
  })

  it('mở kết nối: gửi message xác thực đầu tiên kèm token (dược sĩ), vãng lai không gửi token', () => {
    renderHook(() => usePhongChat({ maPhien: 'p1', vaiTro: 'duoc_si', token: 'tk' }))
    act(() => WsGia.cuoi().mo())
    expect(WsGia.cuoi().gui[0]).toEqual({ loai: 'xac_thuc', vai_tro: 'duoc_si', token: 'tk' })
    renderHook(() => usePhongChat({ maPhien: 'p2', vaiTro: 'khach' }))
    act(() => WsGia.cuoi().mo())
    expect(WsGia.cuoi().gui[0]).toEqual({ loai: 'xac_thuc', vai_tro: 'khach' })
  })

  it('nhận tin, bỏ tin trùng id, báo đang gõ rồi tự tắt, gửi tin chỉ khi đã nối', () => {
    vi.useFakeTimers()
    const { result } = renderHook(() => usePhongChat({ maPhien: 'p1', vaiTro: 'khach' }))
    const s = WsGia.cuoi()
    expect(result.current.trangThai).toBe('dang_noi')
    expect(result.current.gui('xin chào')).toBe(false)
    act(() => { s.mo(); s.nhan({ loai: 'he_thong', su_kien: 'da_ket_noi' }) })
    expect(result.current.trangThai).toBe('da_noi')
    act(() => { s.nhan({ loai: 'tin_nhan', id: 5, vai_tro: 'duoc_si', noi_dung: 'Chào bạn' }); s.nhan({ loai: 'tin_nhan', id: 5, vai_tro: 'duoc_si', noi_dung: 'Chào bạn' }) })
    expect(result.current.tin.map((t) => t.noiDung)).toEqual(['Chào bạn'])
    act(() => s.nhan({ loai: 'dang_go', vai_tro: 'duoc_si' }))
    expect(result.current.doiPhuongDangGo).toBe(true)
    act(() => { vi.advanceTimersByTime(3100) })
    expect(result.current.doiPhuongDangGo).toBe(false)
    expect(result.current.gui('  ')).toBe(false)
    expect(result.current.gui(' Thuốc dùng sao? ')).toBe(true)
    expect(s.gui.at(-1)).toEqual({ loai: 'tin_nhan', noi_dung: 'Thuốc dùng sao?' })
    vi.useRealTimers()
  })

  it('đóng với mã 44xx = bị từ chối, mã khác = mất kết nối; rời thì đóng socket', () => {
    const { result, unmount } = renderHook(() => usePhongChat({ maPhien: 'p1', vaiTro: 'khach' }))
    const s = WsGia.cuoi()
    act(() => s.dongVoi(4404))
    expect(result.current.trangThai).toBe('bi_tu_choi')
    act(() => s.dongVoi(1006))
    expect(result.current.trangThai).toBe('mat_ket_noi')
    unmount()
    expect(s.readyState).toBe(3)
  })
})
