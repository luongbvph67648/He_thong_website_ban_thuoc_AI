import { describe, expect, it } from 'vitest'
import { giaTriTuBanGhi, kiemTraTuongTac, noiDungRaApi, TUONG_TAC_TRONG, type GiaTriTuongTac, type TuongTac } from './tuongTac'

const hopLe = (ghiDe: Partial<GiaTriTuongTac> = {}): GiaTriTuongTac => ({
  ...TUONG_TAC_TRONG,
  hoat_chat_1: { value: 3, label: 'Aspirin' },
  hoat_chat_2: { value: 9, label: 'Warfarin' },
  muc_do: 'nghiem_trong',
  khuyen_cao: 'Không dùng chung',
  ...ghiDe,
})

describe('kiemTraTuongTac (cùng quy tắc với backend schemas_tuong_tac.py)', () => {
  it('hợp lệ thì không có lỗi', () => {
    expect(kiemTraTuongTac(hopLe())).toEqual({})
    expect(kiemTraTuongTac(hopLe({ co_che: 'a\nb', nguon_tham_khao: 'BNF', khuyen_cao: 'x'.repeat(2000) }))).toEqual({})
  })

  it.each<[string, Partial<GiaTriTuongTac>, string]>([
    ['thiếu hoạt chất 1', { hoat_chat_1: null }, 'hoat_chat_1'],
    ['thiếu hoạt chất 2', { hoat_chat_2: null }, 'hoat_chat_2'],
    ['hai hoạt chất giống nhau', { hoat_chat_2: { value: 3, label: 'Aspirin' } }, 'hoat_chat_2'],
    ['chưa chọn mức độ', { muc_do: undefined }, 'muc_do'],
    ['khuyến cáo trống', { khuyen_cao: '   ' }, 'khuyen_cao'],
    ['khuyến cáo quá dài', { khuyen_cao: 'x'.repeat(2001) }, 'khuyen_cao'],
    ['cơ chế có ký tự điều khiển', { co_che: 'a\u0000b' }, 'co_che'],
    ['nguồn quá dài', { nguon_tham_khao: 'x'.repeat(256) }, 'nguon_tham_khao'],
  ])('%s là lỗi ở đúng ô', (_ten, ghiDe, o) => {
    expect(Object.keys(kiemTraTuongTac(hopLe(ghiDe)))).toEqual([o])
  })
})

describe('noiDungRaApi / giaTriTuBanGhi', () => {
  it('ô trống thành null, cắt đầu cuối', () => {
    expect(noiDungRaApi(hopLe({ co_che: '  ', nguon_tham_khao: ' BNF ', khuyen_cao: ' Tránh ' }))).toEqual({ muc_do: 'nghiem_trong', co_che: null, khuyen_cao: 'Tránh', nguon_tham_khao: 'BNF' })
  })

  it('đổi bản ghi API sang giá trị form (null thành chuỗi rỗng, tên hoạt chất giữ nhãn)', () => {
    const ban: TuongTac = {
      hoat_chat_a_id: 3,
      ten_hoat_chat_a: 'Aspirin',
      hoat_chat_b_id: 9,
      ten_hoat_chat_b: 'Warfarin',
      muc_do: 'nhe',
      co_che: null,
      khuyen_cao: 'Theo dõi',
      nguon_tham_khao: null,
      nguoi_cap_nhat: null,
      updated_at: null,
      phien_ban: 'aaaaaaaaaaaaaaaa',
    }
    expect(giaTriTuBanGhi(ban)).toEqual({ hoat_chat_1: { value: 3, label: 'Aspirin' }, hoat_chat_2: { value: 9, label: 'Warfarin' }, muc_do: 'nhe', co_che: '', khuyen_cao: 'Theo dõi', nguon_tham_khao: '' })
  })
})
