import { describe, expect, it } from 'vitest'
import { goi } from './goi'

const LOI = { ma_loi: 'PHAI_CON_ADMIN', thong_diep: 'Phải còn Admin', chi_tiet: null }

describe('goi', () => {
  it('có data thì thành công', async () => {
    expect(await goi(async () => ({ data: { id: 1 }, response: new Response('{}', { status: 200 }) }))).toEqual({ ok: true, data: { id: 1 } })
  })

  it('204 không có thân (DELETE, đăng xuất) vẫn là thành công dù data là undefined', async () => {
    // openapi-fetch trả { data: undefined, response } cho phản hồi 204.
    const kq = await goi(async () => ({ data: undefined, response: new Response(null, { status: 204 }) }))
    expect(kq.ok).toBe(true)
  })

  it('lỗi có thân JSON đúng dạng thì trả lại lỗi đó', async () => {
    const kq = await goi(async () => ({ error: LOI, response: new Response('{}', { status: 409 }) }))
    expect(kq).toEqual({ ok: false, loi: LOI })
  })

  it('lỗi thân rỗng (error là chuỗi rỗng, không phải JSON) vẫn là thất bại, không bị coi là thành công', async () => {
    // openapi-fetch đặt error = await response.text() = '' cho phản hồi lỗi không có thân: phải nhìn response.ok.
    const kq = await goi(async () => ({ data: undefined, error: '', response: new Response('', { status: 502 }) }))
    expect(kq).toEqual({ ok: false, loi: null })
  })

  it('không có phản hồi nào (không có data, không có response) là thất bại', async () => {
    expect(await goi(async () => ({}))).toEqual({ ok: false, loi: null })
  })

  it('lỗi mạng (ném ngoại lệ) là thất bại, không ném tiếp', async () => {
    expect(await goi(async () => Promise.reject(new TypeError('Failed to fetch')))).toEqual({ ok: false, loi: null })
  })
})
