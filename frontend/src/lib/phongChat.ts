import { useCallback, useEffect, useRef, useState } from 'react'

export interface TinTrucTiep {
  khoa: string
  vaiTro: 'khach' | 'ai' | 'duoc_si' | 'he_thong'
  noiDung: string
}

export type TrangThaiNoi = 'dang_noi' | 'da_noi' | 'mat_ket_noi' | 'bi_tu_choi'

interface Tham {
  /** `null` = chưa bật (chưa vào chế độ trực tiếp). */
  maPhien: string | null
  vaiTro: 'khach' | 'duoc_si'
  /** Thành viên hoặc dược sĩ gửi token ở message đầu; vãng lai để trống (mã phiên là bí mật). */
  token?: string | null
  /** Tạo WebSocket (test thay bằng bản giả). */
  taoWs?: (url: string) => WebSocket
}

const macDinh = (url: string) => new WebSocket(url)

export function urlChatWs(maPhien: string, loc: Pick<Location, 'protocol' | 'host'> = globalThis.location): string {
  return `${loc.protocol === 'https:' ? 'wss' : 'ws'}://${loc.host}/api/v1/tu-van/ws?ma_phien=${encodeURIComponent(maPhien)}`
}

/** KTV12/DS06: phòng chat trực tiếp. Token đi trong message đầu tiên, không đặt trên URL. */
export function usePhongChat({ maPhien, vaiTro, token, taoWs = macDinh }: Tham) {
  const [tin, setTin] = useState<TinTrucTiep[]>([])
  const [trangThai, setTrangThai] = useState<TrangThaiNoi>('dang_noi')
  const [doiPhuongDangGo, setDoiPhuongDangGo] = useState(false)
  const ws = useRef<WebSocket | null>(null)
  const dem = useRef(0)
  const hetGo = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const lanGoCuoi = useRef(0)

  useEffect(() => {
    if (!maPhien) return
    const s = taoWs(urlChatWs(maPhien))
    ws.current = s
    setTrangThai('dang_noi')
    s.onopen = () => s.send(JSON.stringify({ loai: 'xac_thuc', vai_tro: vaiTro, ...(token ? { token } : {}) }))
    s.onmessage = (e: MessageEvent) => {
      let d: Record<string, unknown>
      try {
        d = JSON.parse(String(e.data)) as Record<string, unknown>
      } catch {
        return
      }
      if (d.loai === 'tin_nhan') {
        setTin((ds) => (typeof d.id === 'number' && ds.some((t) => t.khoa === `s${d.id}`) ? ds : [...ds, { khoa: `s${String(d.id ?? ++dem.current)}`, vaiTro: d.vai_tro as TinTrucTiep['vaiTro'], noiDung: String(d.noi_dung ?? '') }]))
        setDoiPhuongDangGo(false)
      } else if (d.loai === 'dang_go') {
        setDoiPhuongDangGo(true)
        clearTimeout(hetGo.current)
        hetGo.current = setTimeout(() => setDoiPhuongDangGo(false), 3000)
      } else if (d.loai === 'he_thong') {
        if (d.su_kien === 'da_ket_noi') setTrangThai('da_noi')
        else if (d.su_kien === 'duoc_si_vao') setTin((ds) => [...ds, { khoa: `h${++dem.current}`, vaiTro: 'he_thong', noiDung: `Dược sĩ ${String(d.ten ?? '')} đã tham gia cuộc trò chuyện.` }])
        else if (d.su_kien === 'loi') setTin((ds) => [...ds, { khoa: `h${++dem.current}`, vaiTro: 'he_thong', noiDung: String(d.thong_diep ?? 'Không gửi được tin nhắn') }])
      }
    }
    s.onclose = (e: CloseEvent) => setTrangThai(e.code >= 4400 && e.code < 4500 ? 'bi_tu_choi' : 'mat_ket_noi')
    return () => {
      clearTimeout(hetGo.current)
      s.onclose = null
      s.close()
      ws.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [maPhien, vaiTro, token])

  const gui = useCallback((noiDung: string) => {
    const nd = noiDung.trim()
    if (!nd || ws.current?.readyState !== 1) return false
    ws.current.send(JSON.stringify({ loai: 'tin_nhan', noi_dung: nd }))
    return true
  }, [])
  const baoDangGo = useCallback(() => {
    const bay = Date.now()
    if (ws.current?.readyState === 1 && bay - lanGoCuoi.current > 2000) {
      lanGoCuoi.current = bay
      ws.current.send(JSON.stringify({ loai: 'dang_go' }))
    }
  }, [])
  const datTin = setTin
  return { tin, trangThai, doiPhuongDangGo, gui, baoDangGo, datTin }
}
