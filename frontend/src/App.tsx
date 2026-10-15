import { useEffect, useState } from 'react'

type SucKhoe = { trang_thai: string; db: string }
type TrangThai =
  | { loai: 'dang-tai' }
  | { loai: 'co-du-lieu'; du_lieu: SucKhoe }
  | { loai: 'khong-ket-noi' }

export default function App() {
  const [trangThai, setTrangThai] = useState<TrangThai>({ loai: 'dang-tai' })

  useEffect(() => {
    const huy = new AbortController()
    fetch('/api/v1/health', { signal: huy.signal })
      .then((resp) => resp.json() as Promise<SucKhoe>)
      .then((du_lieu) => setTrangThai({ loai: 'co-du-lieu', du_lieu }))
      .catch((loi: unknown) => {
        if (!(loi instanceof DOMException && loi.name === 'AbortError')) {
          setTrangThai({ loai: 'khong-ket-noi' })
        }
      })
    return () => huy.abort()
  }, [])

  return (
    <main style={{ padding: 24 }}>
      <h1>Nhà thuốc AI</h1>
      <p data-testid="trang-thai-backend">
        {trangThai.loai === 'dang-tai' && 'Đang kiểm tra backend…'}
        {trangThai.loai === 'khong-ket-noi' && 'Không kết nối được backend'}
        {trangThai.loai === 'co-du-lieu' &&
          `Backend: ${trangThai.du_lieu.trang_thai} · CSDL: ${trangThai.du_lieu.db}`}
      </p>
    </main>
  )
}
