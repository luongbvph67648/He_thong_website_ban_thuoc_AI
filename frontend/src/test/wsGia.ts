/** WebSocket giả cho test: ghi lại message gửi đi, test chủ động mở/nhận/đóng. */
export class WsGia {
  static tatCa: WsGia[] = []
  readyState = 0
  gui: unknown[] = []
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: ((e: { code: number }) => void) | null = null
  url: string
  constructor(url: string) {
    this.url = url
    WsGia.tatCa.push(this)
  }
  send(d: string) {
    this.gui.push(JSON.parse(d))
  }
  close() {
    this.readyState = 3
  }
  mo() {
    this.readyState = 1
    this.onopen?.()
  }
  nhan(d: object) {
    this.onmessage?.({ data: JSON.stringify(d) })
  }
  dongVoi(code: number) {
    this.readyState = 3
    this.onclose?.({ code })
  }
  static cuoi() {
    return WsGia.tatCa[WsGia.tatCa.length - 1]!
  }
}
