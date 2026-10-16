import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { KHOA_QUERY_CUA_HANG } from './cuaHang'

/** Hook dùng chung cho menu, trang chủ và trang danh mục: cây danh mục đang hiển thị. */
export function useCayDanhMuc() {
  return useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'danh-muc'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/danh-muc')
      if (error || !data) throw new Error('Không tải được danh mục')
      return data
    },
    staleTime: 5 * 60_000,
  })
}
