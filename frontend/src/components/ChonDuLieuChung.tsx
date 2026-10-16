import { useQuery } from '@tanstack/react-query'
import { Select } from 'antd'
import { useEffect, useState } from 'react'
import { danhSach } from '../khu/quan-tri/du-lieu-chung/goiApi'
import { KHOA_QUERY_DU_LIEU_CHUNG, type MaNhom } from '../khu/quan-tri/du-lieu-chung/nhom'

/** Giá trị của ô chọn: id kèm tên để hiện được ngay cả khi bản ghi chưa nằm trong trang kết quả tìm. */
export interface LuaChon {
  value: number
  label: string
}

interface Props {
  ma: MaNhom
  value?: LuaChon | null
  onChange?: (v: LuaChon | null) => void
  placeholder: string
  id?: string
  /** Tên truy cập của ô (khi không có nhãn đi kèm, ví dụ ô trong bảng). */
  nhan?: string
  disabled?: boolean
  /** Bắt buộc chọn (không có nút xóa). */
  batBuoc?: boolean
}

const SO_KET_QUA = 20
const TRE_GO_MS = 300

/**
 * Ô chọn thương hiệu / nhà sản xuất / hoạt chất theo kiểu tìm trên máy chủ (danh sách có thể dài hàng nghìn dòng nên
 * không tải hết). Chỉ lấy một trang kết quả đầu cho từ khóa đang gõ.
 */
export function ChonDuLieuChung({ ma, value, onChange, placeholder, id, nhan, disabled, batBuoc }: Props) {
  const [go, setGo] = useState('')
  const [tuKhoa, setTuKhoa] = useState('')
  useEffect(() => {
    const h = setTimeout(() => setTuKhoa(go.trim()), TRE_GO_MS)
    return () => clearTimeout(h)
  }, [go])

  const ketQua = useQuery({
    queryKey: [...KHOA_QUERY_DU_LIEU_CHUNG, 'chon', ma, tuKhoa],
    queryFn: async () => {
      const kq = await danhSach(ma, { q: tuKhoa || undefined, sap_xep: 'ten', trang: 1, kich_thuoc: SO_KET_QUA })
      if (!kq.ok) throw kq.loi ?? new Error('Không tải được danh sách')
      return kq.data.du_lieu
    },
    staleTime: 30_000,
  })

  const tuyChon = (ketQua.data ?? []).map((b) => ({ value: b.id, label: b.ten }))
  // Giá trị đang chọn có thể không nằm trong trang kết quả của từ khóa hiện tại: vẫn phải hiện đúng tên.
  if (value && !tuyChon.some((o) => o.value === value.value)) tuyChon.unshift({ value: value.value, label: value.label })

  return (
    <Select<LuaChon>
      id={id}
      aria-label={nhan}
      showSearch
      allowClear={!batBuoc}
      labelInValue
      filterOption={false}
      disabled={disabled}
      placeholder={placeholder}
      value={value ?? undefined}
      options={tuyChon}
      loading={ketQua.isFetching}
      notFoundContent={ketQua.isError ? 'Không tải được danh sách' : 'Không có kết quả'}
      onSearch={setGo}
      onOpenChange={(mo) => {
        if (!mo) setGo('')
      }}
      onChange={(v) => onChange?.(v ? { value: Number(v.value), label: String(v.label) } : null)}
    />
  )
}
