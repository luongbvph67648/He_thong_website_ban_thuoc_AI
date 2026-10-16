import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { api } from '../../../api/client'
import { KHOA_QUERY_DANH_MUC } from '../danh-muc/danhMuc'
import { cayChoTreeSelect } from './sanPham'

/** Cây danh mục (AD03) cho ô lọc và ô chọn danh mục; dùng chung query với trang danh mục nên mọi nơi cùng làm mới. */
export function useCayDanhMuc() {
  const cay = useQuery({
    queryKey: KHOA_QUERY_DANH_MUC,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/danh-muc')
      if (error) throw error
      return data
    },
    staleTime: 60_000,
  })
  const tuyChon = useMemo(() => cayChoTreeSelect(cay.data ?? []), [cay.data])
  return { cay, tuyChon }
}
