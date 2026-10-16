import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Collapse, Empty, Skeleton, Typography } from 'antd'
import { api } from '../../api/client'
import { NoiDungMarkdown } from '../../components/NoiDungMarkdown'
import { KHOA_QUERY_BAI_VIET } from './noiDungWebKhach'

/** Hỏi đáp thường gặp (FAQ, KVL11): mỗi bài `faq` là một câu hỏi (tiêu đề) và câu trả lời (Markdown). */
export default function TrangHoiDap() {
  const ds = useQuery({
    queryKey: [...KHOA_QUERY_BAI_VIET, 'faq'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/bai-viet', { params: { query: { loai: 'faq', kem_noi_dung: true, kich_thuoc: 100 } } })
      if (error || !data) throw error ?? new Error('Không tải được câu hỏi')
      return data
    },
  })
  return (
    <article style={{ maxWidth: 820, margin: '0 auto' }}>
      <Typography.Title level={1}>Hỏi đáp thường gặp</Typography.Title>
      {ds.isPending ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : ds.isError ? (
        <Alert type="error" showIcon title="Không tải được câu hỏi" action={<Button onClick={() => void ds.refetch()}>Thử lại</Button>} />
      ) : ds.data.du_lieu.length === 0 ? (
        <Empty description="Chưa có câu hỏi nào" />
      ) : (
        <Collapse
          items={ds.data.du_lieu.map((b) => ({
            key: b.id,
            label: b.tieu_de,
            children: b.noi_dung ? <NoiDungMarkdown noiDung={b.noi_dung} /> : null,
          }))}
        />
      )}
    </article>
  )
}
