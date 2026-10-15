import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { api } from '../api/client'
import { phienTuNhanVien } from '../lib/hoSoNoiBo'
import { usePhien } from '../stores/phien'

const CHU_KY_MS = 5 * 60_000

/**
 * Giữ quyền, vai trò và cờ đổi mật khẩu của phiên nội bộ khớp với máy chủ: Admin đổi phân quyền (AD18) hoặc vai trò
 * (AD01) thì menu của nhân viên đang đăng nhập cập nhật khi họ quay lại cửa sổ hoặc sau tối đa 5 phút, không cần đăng
 * nhập lại. Chỉ là lớp giao diện: máy chủ luôn kiểm tra quyền thật ở mỗi request.
 */
export function useDongBoPhienNoiBo(): void {
  const { data } = useQuery({
    queryKey: ['noi-bo', 'toi'],
    refetchInterval: CHU_KY_MS,
    refetchOnWindowFocus: 'always',
    staleTime: 30_000,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/toi')
      if (error) throw error
      return data
    },
  })
  useEffect(() => {
    if (data?.vai_tro && data.quyen) usePhien.getState().capNhatTuMayChu(phienTuNhanVien(data))
  }, [data])
}
