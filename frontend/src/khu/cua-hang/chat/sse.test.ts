import { describe, expect, it } from 'vitest'
import { docSse } from './sse'

function luong(...phan: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder()
  return new ReadableStream({
    start(c) {
      phan.forEach((p) => c.enqueue(enc.encode(p)))
      c.close()
    },
  })
}

describe('docSse', () => {
  it('ghép sự kiện bị cắt giữa chừng và giữ tiếng Việt có dấu', async () => {
    const ds: [string, unknown][] = []
    await docSse(luong('event: van_ban\ndata: {"noi_dung":"Xin ch', 'ào"}\n\nevent: ket_thuc\ndata: {"tin_nhan_id":3}\n\n'), (l, d) => ds.push([l, d]))
    expect(ds).toEqual([['van_ban', { noi_dung: 'Xin chào' }], ['ket_thuc', { tin_nhan_id: 3 }]])
  })
  it('bỏ qua khối JSON hỏng', async () => {
    const ds: string[] = []
    await docSse(luong('event: a\ndata: {hong\n\nevent: b\ndata: {}\n\n'), (l) => ds.push(l))
    expect(ds).toEqual(['b'])
  })
})
