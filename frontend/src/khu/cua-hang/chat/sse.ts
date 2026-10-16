/** Đọc luồng `text/event-stream` (sự kiện dạng `event: x\ndata: {json}\n\n`) và gọi `khiSuKien(loai, dữ liệu)` cho từng sự kiện. */
export async function docSse(
  luong: ReadableStream<Uint8Array>,
  khiSuKien: (loai: string, duLieu: Record<string, unknown>) => void,
): Promise<void> {
  const doc = luong.getReader()
  const giaiMa = new TextDecoder()
  let dem = ''
  for (;;) {
    const { done, value } = await doc.read()
    if (done) break
    dem += giaiMa.decode(value, { stream: true }).replaceAll('\r\n', '\n')
    let cat = dem.indexOf('\n\n')
    while (cat >= 0) {
      const khoi = dem.slice(0, cat)
      dem = dem.slice(cat + 2)
      xuLyKhoi(khoi, khiSuKien)
      cat = dem.indexOf('\n\n')
    }
  }
  if (dem.trim()) xuLyKhoi(dem, khiSuKien)
}

function xuLyKhoi(khoi: string, khiSuKien: (loai: string, duLieu: Record<string, unknown>) => void): void {
  let loai = 'message'
  const data: string[] = []
  for (const dong of khoi.split('\n')) {
    if (dong.startsWith('event:')) loai = dong.slice(6).trim()
    else if (dong.startsWith('data:')) data.push(dong.slice(5).replace(/^ /, ''))
  }
  if (data.length === 0) return
  try {
    khiSuKien(loai, JSON.parse(data.join('\n')) as Record<string, unknown>)
  } catch {
    /* bỏ qua khối hỏng, không làm đứt luồng */
  }
}
