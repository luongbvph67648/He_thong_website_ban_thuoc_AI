import { useQuery } from '@tanstack/react-query'
import { Space, Typography } from 'antd'
import { Layout } from 'antd'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { KHOA_QUERY_BAI_VIET } from './noiDungWebKhach'

/** Chân trang cửa hàng: liên kết bài viết, hỏi đáp và các trang chính sách đã đăng (lỗi tải thì chỉ ẩn phần chính sách). */
export function ChanTrang() {
  const chinhSach = useQuery({
    queryKey: [...KHOA_QUERY_BAI_VIET, 'chinh-sach'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/bai-viet', { params: { query: { loai: 'chinh_sach', kich_thuoc: 20 } } })
      if (error || !data) throw new Error('Không tải được chính sách')
      return data.du_lieu
    },
    staleTime: 5 * 60_000,
  })
  return (
    <Layout.Footer style={{ textAlign: 'center' }}>
      <Space separator="·" wrap style={{ justifyContent: 'center' }}>
        <Link to="/bai-viet">Bài viết</Link>
        <Link to="/hoi-dap">Hỏi đáp</Link>
        {(chinhSach.data ?? []).map((c) => (
          <Link key={c.id} to={`/chinh-sach/${encodeURIComponent(c.slug)}`}>
            {c.tieu_de}
          </Link>
        ))}
      </Space>
      <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
        Thông tin trên website chỉ mang tính tham khảo, không thay thế tư vấn của dược sĩ hoặc bác sĩ.
      </Typography.Paragraph>
    </Layout.Footer>
  )
}
