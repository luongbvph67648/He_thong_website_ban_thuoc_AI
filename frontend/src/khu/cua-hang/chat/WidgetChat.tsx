import { CloseOutlined, DislikeOutlined, MessageOutlined, SendOutlined } from '@ant-design/icons'
import { Alert, Button, FloatButton, Input, Space, Typography } from 'antd'
import { usePhien } from '../../../stores/phien'
import { usePhongChat } from '../../../lib/phongChat'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangTien } from '../../../lib/dinhDang'
import { docSse } from './sse'

type SanPhamThe = components['schemas']['SanPhamThe']
interface TinNhan {
  khoa: number
  id?: number
  vaiTro: 'khach' | 'ai'
  noiDung: string
  the?: SanPhamThe[]
  nguyHiem?: boolean
  chuyenDuocSi?: boolean
  baoSai?: boolean
}

const KHOA_PHIEN = 'chat_ma_phien'

/** Mã phiên chat (UUID) giữ trong sessionStorage: đóng tab là bắt đầu cuộc trò chuyện mới. Không chứa thông tin cá nhân. */
function layMaPhien(): string {
  try {
    const cu = sessionStorage.getItem(KHOA_PHIEN)
    if (cu) return cu
    const moi = globalThis.crypto.randomUUID()
    sessionStorage.setItem(KHOA_PHIEN, moi)
    return moi
  } catch {
    return globalThis.crypto.randomUUID()
  }
}

/** KVL05: chat với trợ lý AI (SSE) — luôn nằm góc phải dưới trên mọi trang cửa hàng. */
export default function WidgetChat() {
  const [mo, setMo] = useState(false)
  const [tin, setTin] = useState<TinNhan[]>([])
  const [nhap, setNhap] = useState('')
  const [dang, setDang] = useState(false)
  const [loi, setLoi] = useState<string | null>(null)
  const maPhien = useRef<string>('')
  const token = usePhien((st) => st.accessToken)
  const loaiPhien = usePhien((st) => st.loai)
  const [truc, setTruc] = useState<null | { maPhien: string; trangThai: 'cho_duoc_si' | 'cho_goi_lai'; thongDiep: string }>(null)
  const [hoiSdt, setHoiSdt] = useState(false)
  const [sdt, setSdt] = useState('')
  const [dangGap, setDangGap] = useState(false)
  const phong = usePhongChat({ maPhien: truc?.trangThai === 'cho_duoc_si' ? truc.maPhien : null, vaiTro: 'khach', token: loaiPhien === 'khach' ? token : null })
  const khoaTiep = useRef(1)
  const cuoi = useRef<HTMLDivElement>(null)
  useEffect(() => { cuoi.current?.scrollIntoView?.({ block: 'end' }) }, [tin, mo])

  const capNhatCuoi = (f: (t: TinNhan) => TinNhan) => setTin((ds) => ds.map((t, i) => (i === ds.length - 1 ? f(t) : t)))

  async function gui() {
    const noiDung = nhap.trim()
    if (!noiDung || dang) return
    if (truc?.trangThai === 'cho_duoc_si') {
      if (phong.gui(noiDung)) setNhap('')
      return
    }
    maPhien.current ||= layMaPhien()
    setLoi(null)
    setNhap('')
    setDang(true)
    setTin((ds) => [...ds, { khoa: khoaTiep.current++, vaiTro: 'khach', noiDung }, { khoa: khoaTiep.current++, vaiTro: 'ai', noiDung: '' }])
    try {
      const { data, response } = await api.POST('/api/v1/tu-van/chat', {
        body: { ma_phien: maPhien.current, noi_dung: noiDung },
        parseAs: 'stream',
      })
      if (!response.ok || !data) {
        setTin((ds) => ds.slice(0, -1))
        setLoi(response.status === 429 ? 'Bạn hỏi quá nhanh, vui lòng chờ một lúc rồi hỏi tiếp.' : 'Không gửi được tin nhắn, vui lòng thử lại.')
        return
      }
      await docSse(data as ReadableStream<Uint8Array>, (loai, d) => {
        if (loai === 'van_ban') capNhatCuoi((t) => ({ ...t, noiDung: t.noiDung + String(d.noi_dung ?? '') }))
        else if (loai === 'nguy_hiem') capNhatCuoi((t) => ({ ...t, noiDung: String(d.noi_dung ?? ''), nguyHiem: true }))
        else if (loai === 'the_san_pham') capNhatCuoi((t) => ({ ...t, the: d.san_pham as SanPhamThe[] }))
        else if (loai === 'chuyen_duoc_si') capNhatCuoi((t) => ({ ...t, noiDung: t.noiDung || String(d.thong_diep ?? ''), chuyenDuocSi: true }))
        else if (loai === 'ket_thuc') capNhatCuoi((t) => ({ ...t, id: Number(d.tin_nhan_id) }))
        else if (loai === 'loi') setLoi(String(d.thong_diep ?? 'Có lỗi xảy ra'))
      })
    } catch {
      setLoi('Mất kết nối, vui lòng thử lại.')
    } finally {
      setDang(false)
    }
  }

  async function gapDuocSi(soDt?: string) {
    maPhien.current ||= layMaPhien()
    setDangGap(true)
    setLoi(null)
    const r = await goi(() => api.POST('/api/v1/tu-van/gap-duoc-si', { body: { ma_phien: maPhien.current, ...(soDt ? { so_dien_thoai: soDt } : {}) } }))
    setDangGap(false)
    if (!r.ok) {
      const can = (r.loi?.chi_tiet as { truong?: string }[] | null)?.some?.((c) => c.truong === 'so_dien_thoai')
      if (can) setHoiSdt(true)
      setLoi(can ? 'Hiện ngoài giờ làm việc của dược sĩ, vui lòng để lại số điện thoại để được gọi lại.' : thongDiepChung(r.loi))
      return
    }
    setHoiSdt(false)
    setTruc({ maPhien: maPhien.current, trangThai: r.data.trang_thai, thongDiep: r.data.thong_diep })
  }

  async function baoSai(t: TinNhan) {
    if (t.id === undefined || t.baoSai) return
    setTin((ds) => ds.map((x) => (x.khoa === t.khoa ? { ...x, baoSai: true } : x)))
    await api.POST('/api/v1/tu-van/danh-gia', { body: { ma_phien: maPhien.current, tin_nhan_id: t.id, ket_qua: 'khong_huu_ich' } })
  }

  return (
    <>
      {!mo && <FloatButton icon={<MessageOutlined />} type="primary" tooltip="Hỏi trợ lý nhà thuốc" aria-label="Mở chat tư vấn" onClick={() => setMo(true)} />}
      {mo && (
        <section aria-label="Chat tư vấn" style={{ position: 'fixed', right: 16, bottom: 16, width: 'min(380px, calc(100vw - 32px))', height: 'min(560px, calc(100vh - 32px))', background: '#fff', border: '1px solid #d9d9d9', borderRadius: 8, boxShadow: '0 6px 24px rgba(0,0,0,.18)', display: 'flex', flexDirection: 'column', zIndex: 1000 }}>
          <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', borderBottom: '1px solid #f0f0f0' }}>
            <Typography.Text strong>Trợ lý nhà thuốc</Typography.Text>
            <Button type="text" aria-label="Đóng chat" icon={<CloseOutlined />} onClick={() => setMo(false)} />
          </header>
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
            <Alert type="info" showIcon style={{ marginBottom: 8 }} title="Mình là trợ lý AI, chỉ tư vấn thông tin tham khảo về thuốc không kê đơn. Không thay thế dược sĩ/bác sĩ." />
            {tin.map((t) => (
              <div key={t.khoa} style={{ display: 'flex', flexDirection: 'column', alignItems: t.vaiTro === 'khach' ? 'flex-end' : 'flex-start', marginBottom: 8 }}>
                <div style={{ maxWidth: '90%', padding: '6px 10px', borderRadius: 8, whiteSpace: 'pre-wrap', background: t.vaiTro === 'khach' ? '#e6f4ff' : t.nguyHiem ? '#fff1f0' : '#f5f5f5' }}>
                  {t.noiDung || (dang ? '…' : '')}
                </div>
                {t.the && t.the.length > 0 && (
                  <Space orientation="vertical" size={4} style={{ marginTop: 4, width: '90%' }}>
                    {t.the.map((s) => (
                      <Link key={s.id} to={`/san-pham/${s.slug}`} onClick={() => setMo(false)} style={{ display: 'block', border: '1px solid #f0f0f0', borderRadius: 6, padding: '4px 8px' }}>
                        <div>{s.ten}</div>
                        <Typography.Text type="secondary">{s.gia ? `Từ ${dinhDangTien(s.gia)}` : 'Liên hệ'}{s.con_hang ? '' : ' · Hết hàng'}</Typography.Text>
                      </Link>
                    ))}
                  </Space>
                )}
                {t.vaiTro === 'ai' && t.id !== undefined && (
                  <Button size="small" type="text" icon={<DislikeOutlined />} disabled={t.baoSai} onClick={() => void baoSai(t)}>{t.baoSai ? 'Đã báo' : 'Báo sai'}</Button>
                )}
              </div>
            ))}
            {truc && <Alert type="success" showIcon style={{ marginBottom: 8 }} title={truc.thongDiep} />}
            {phong.tin.map((t) => (
              <div key={t.khoa} style={{ display: 'flex', flexDirection: 'column', alignItems: t.vaiTro === 'khach' ? 'flex-end' : 'flex-start', marginBottom: 8 }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t.vaiTro === 'duoc_si' ? 'Dược sĩ' : t.vaiTro === 'khach' ? 'Bạn' : 'Hệ thống'}</Typography.Text>
                <div style={{ maxWidth: '90%', padding: '6px 10px', borderRadius: 8, whiteSpace: 'pre-wrap', background: t.vaiTro === 'khach' ? '#e6f4ff' : '#f5f5f5' }}>{t.noiDung}</div>
              </div>
            ))}
            {phong.doiPhuongDangGo && <Typography.Text type="secondary">Dược sĩ đang nhập…</Typography.Text>}
            <div ref={cuoi} />
          </div>
          {loi && <Alert type="error" showIcon title={loi} style={{ margin: '0 12px' }} />}
          {hoiSdt && (
            <Space.Compact style={{ margin: '8px 12px 0' }}>
              <Input aria-label="Số điện thoại để dược sĩ gọi lại" inputMode="tel" maxLength={20} placeholder="Số điện thoại" value={sdt} onChange={(e) => setSdt(e.target.value)} />
              <Button type="primary" loading={dangGap} disabled={!sdt.trim()} onClick={() => void gapDuocSi(sdt.trim())}>Gửi</Button>
            </Space.Compact>
          )}
          {!truc && !hoiSdt && tin.some((t) => t.vaiTro === 'khach') && (
            <Button type="link" style={{ alignSelf: 'flex-start' }} loading={dangGap} onClick={() => void gapDuocSi()}>Gặp dược sĩ</Button>
          )}
          <footer style={{ display: 'flex', gap: 8, padding: 12, borderTop: '1px solid #f0f0f0' }}>
            <Input aria-label="Tin nhắn" value={nhap} maxLength={1000} placeholder="Nhập câu hỏi…" onPressEnter={() => void gui()} disabled={dang || truc?.trangThai === 'cho_goi_lai'} onChange={(e) => { setNhap(e.target.value); if (truc?.trangThai === 'cho_duoc_si') phong.baoDangGo() }} />
            <Button type="primary" aria-label="Gửi" icon={<SendOutlined />} loading={dang} disabled={!nhap.trim()} onClick={() => void gui()} />
          </footer>
        </section>
      )}
    </>
  )
}
