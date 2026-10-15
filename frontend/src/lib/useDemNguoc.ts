import { useCallback, useEffect, useState } from 'react'

/** Đếm ngược theo giây (nút "Gửi lại mã"). Trả `[giây còn lại, hàm bắt đầu đếm]`. */
export function useDemNguoc(): [number, (giay: number) => void] {
  const [giayCon, setGiayCon] = useState(0)
  const dangDem = giayCon > 0
  useEffect(() => {
    if (!dangDem) return
    const dong = setInterval(() => setGiayCon((g) => Math.max(0, g - 1)), 1000)
    return () => clearInterval(dong)
  }, [dangDem])
  return [giayCon, useCallback((giay: number) => setGiayCon(giay), [])]
}
