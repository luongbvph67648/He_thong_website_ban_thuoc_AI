import { SearchOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { AutoComplete, Input, Tag } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { KHOA_QUERY_CUA_HANG } from './cuaHang'
import { chuanHoaTuKhoa, duDieuKienTim, duongDanGoiY, duongDanTimKiem, TRE_GOI_Y_MS, type GoiY } from './timKiem'

/** Ô tìm kiếm ở header: gợi ý khi gõ (trễ 250 ms, từ 2 ký tự); Enter hoặc nút tìm chạy tìm kiếm đầy đủ. */
export function OTimKiem() {
  const [go, datGo] = useState('')
  const [daTre, datDaTre] = useState('')
  const dieuHuong = useNavigate()

  useEffect(() => {
    const h = setTimeout(() => datDaTre(chuanHoaTuKhoa(go)), TRE_GOI_Y_MS)
    return () => clearTimeout(h)
  }, [go])

  const goiY = useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'goi-y', daTre],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/tim-kiem/goi-y', { params: { query: { q: daTre } } })
      if (error || !data) throw new Error('Không tải được gợi ý')
      return data
    },
    enabled: duDieuKienTim(daTre),
    staleTime: 60_000,
  })
  const danhSach: GoiY[] = duDieuKienTim(daTre) ? (goiY.data ?? []) : []

  const timDayDu = (q: string) => {
    if (duDieuKienTim(q)) dieuHuong(duongDanTimKiem(q))
  }

  return (
    <AutoComplete
      style={{ flex: '1 1 240px', maxWidth: 560 }}
      value={go}
      onChange={datGo}
      popupMatchSelectWidth
      options={danhSach.map((g, i) => ({
        // Giá trị phải duy nhất (sản phẩm và hoạt chất có thể trùng tên) nên hoạt chất mang hậu tố; đích đi theo `goiY`.
        value: g.kieu === 'hoat_chat' ? `${g.ten} (hoạt chất)` : g.ten,
        key: `${g.kieu}-${i}`,
        goiY: g,
        label: (
          <span>
            {g.ten} {g.kieu === 'hoat_chat' && <Tag>Hoạt chất</Tag>}
            {g.can_tu_van && <Tag color="volcano">Cần tư vấn</Tag>}
          </span>
        ),
      }))}
      onSelect={(_, opt) => dieuHuong(duongDanGoiY((opt as { goiY: GoiY }).goiY))}
    >
      <Input.Search
        placeholder="Tìm thuốc, thực phẩm chức năng, thiết bị y tế…"
        aria-label="Tìm kiếm"
        allowClear
        enterButton={<SearchOutlined aria-label="Tìm" />}
        maxLength={100}
        onSearch={timDayDu}
      />
    </AutoComplete>
  )
}
