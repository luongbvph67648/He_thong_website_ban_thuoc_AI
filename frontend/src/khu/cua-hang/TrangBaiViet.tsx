import { useQuery } from '@tanstack/react-query'
import { Alert, Breadcrumb, Button, Result, Skeleton, Typography } from 'antd'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../api/client'
import { laLoiApi } from '../../api/loi'
import { NoiDungMarkdown } from '../../components/NoiDungMarkdown'
import { dinhDangNgay } from '../../lib/dinhDang'
import { lienKetAnToan } from '../../lib/lienKet'
import { LOI_KHONG_CO } from './cuaHang'
import { KHOA_QUERY_BAI_VIET, type LoaiBaiCongKhai } from './noiDungWebKhach'

const TEN_LOAI: Record<'bai_viet' | 'chinh_sach', { muc: string; ve: string; tro: string }> = {
  bai_viet: { muc: 'Bài viết sức khỏe', ve: '/bai-viet', tro: 'Bài viết không tồn tại hoặc chưa được đăng.' },
  chinh_sach: { muc: 'Chính sách', ve: '/', tro: 'Trang chính sách không tồn tại hoặc chưa được đăng.' },
}

/** Đọc một bài viết sức khỏe hoặc một trang chính sách theo slug (KVL11). Slug thuộc loại khác (FAQ, hoặc nhầm đường dẫn) là 404. */
export default function TrangBaiViet({ loai }: { loai: Exclude<LoaiBaiCongKhai, 'faq'> }) {
  const { slug = '' } = useParams()
  const ten = TEN_LOAI[loai]
  const bai = useQuery({
    queryKey: [...KHOA_QUERY_BAI_VIET, 'chi-tiet', slug],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/bai-viet/{slug}', { params: { path: { slug } } })
      if (error || !data) throw error ?? new Error('Không tải được bài viết')
      return data
    },
  })

  if (bai.isPending) return <Skeleton active paragraph={{ rows: 10 }} />
  const khongCo = bai.isError ? laLoiApi(bai.error) && LOI_KHONG_CO.has(bai.error.ma_loi) : bai.data.loai !== loai
  if (khongCo) return <Result status="404" title="Không tìm thấy trang" subTitle={ten.tro} extra={<Link to={ten.ve}>{loai === 'bai_viet' ? 'Xem các bài viết' : 'Về trang chủ'}</Link>} />
  if (bai.isError) return <Alert type="error" showIcon title="Không tải được trang" action={<Button onClick={() => void bai.refetch()}>Thử lại</Button>} />
  const b = bai.data
  const anh = lienKetAnToan(b.anh_bia_url)
  return (
    <article style={{ maxWidth: 820, margin: '0 auto' }}>
      <Breadcrumb items={[{ title: <Link to="/">Trang chủ</Link> }, ...(loai === 'bai_viet' ? [{ title: <Link to="/bai-viet">{ten.muc}</Link> }] : []), { title: b.tieu_de }]} />
      <Typography.Title level={1} style={{ marginTop: 12 }}>
        {b.tieu_de}
      </Typography.Title>
      <Typography.Text type="secondary">{dinhDangNgay(b.ngay_dang, 'ngay')}</Typography.Text>
      {anh && <img src={anh} alt="" style={{ width: '100%', maxHeight: 360, objectFit: 'cover', margin: '16px 0' }} />}
      <div style={{ marginTop: 16 }}>
        <NoiDungMarkdown noiDung={b.noi_dung} />
      </div>
      {loai === 'bai_viet' && (
        <Typography.Paragraph type="secondary" style={{ marginTop: 24 }}>
          Nội dung chỉ mang tính tham khảo, không thay thế tư vấn của bác sĩ hoặc dược sĩ.
        </Typography.Paragraph>
      )}
    </article>
  )
}
