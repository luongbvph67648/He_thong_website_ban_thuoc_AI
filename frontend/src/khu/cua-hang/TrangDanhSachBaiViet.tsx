import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Empty, Input, Pagination, Skeleton, Typography } from 'antd'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../api/client'
import { dinhDangNgay } from '../../lib/dinhDang'
import { lienKetAnToan } from '../../lib/lienKet'
import { duongDanBai, KHOA_QUERY_BAI_VIET, KICH_THUOC_DS_BAI } from './noiDungWebKhach'

/** Danh sách bài viết sức khỏe đã đăng (KVL11). Từ khóa và trang nằm trên URL. */
export default function TrangDanhSachBaiViet() {
  const [tham, datTham] = useSearchParams()
  const q = (tham.get('q') ?? '').slice(0, 100)
  const trang = Math.max(1, Number(tham.get('trang')) || 1)
  const doi = (moi: Record<string, string>) => datTham(new URLSearchParams(Object.entries(moi).filter(([, v]) => v)), { replace: true })

  const ds = useQuery({
    queryKey: [...KHOA_QUERY_BAI_VIET, 'danh-sach', q, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/bai-viet', { params: { query: { loai: 'bai_viet', q: q.trim() || undefined, trang, kich_thuoc: KICH_THUOC_DS_BAI } } })
      if (error || !data) throw error ?? new Error('Không tải được bài viết')
      return data
    },
    placeholderData: (truoc) => truoc,
  })

  return (
    <>
      <Typography.Title level={2}>Bài viết sức khỏe</Typography.Title>
      <Typography.Paragraph type="secondary">Bài viết do nhà thuốc biên soạn và được dược sĩ duyệt. Chỉ mang tính tham khảo, không thay thế tư vấn của bác sĩ hoặc dược sĩ.</Typography.Paragraph>
      <Input.Search key={q} allowClear aria-label="Tìm bài viết" placeholder="Tìm theo tiêu đề" defaultValue={q} maxLength={100} style={{ maxWidth: 420, marginBottom: 16 }} onSearch={(v) => doi({ q: v.trim() })} />
      {ds.isError && !ds.data ? (
        <Alert type="error" showIcon title="Không tải được bài viết" action={<Button onClick={() => void ds.refetch()}>Thử lại</Button>} />
      ) : ds.isPending ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : ds.data.du_lieu.length === 0 && ds.data.tong > 0 ? (
        <Empty description="Trang này không có bài viết">
          <Button onClick={() => doi({ q })}>Về trang 1</Button>
        </Empty>
      ) : ds.data.du_lieu.length === 0 ? (
        <Empty description={q ? 'Không có bài viết phù hợp' : 'Chưa có bài viết'} />
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
            {ds.data.du_lieu.map((b) => {
              const anh = lienKetAnToan(b.anh_bia_url)
              return (
                <Link key={b.id} to={duongDanBai(b.loai, b.slug)} aria-label={b.tieu_de}>
                  <Card hoverable size="small" style={{ height: '100%' }} cover={anh ? <img src={anh} alt="" loading="lazy" style={{ height: 150, objectFit: 'cover' }} /> : undefined}>
                    <Typography.Text strong>{b.tieu_de}</Typography.Text>
                    <Typography.Paragraph type="secondary" ellipsis={{ rows: 3 }} style={{ margin: '8px 0' }}>
                      {b.tom_tat}
                    </Typography.Paragraph>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {dinhDangNgay(b.ngay_dang, 'ngay')}
                    </Typography.Text>
                  </Card>
                </Link>
              )
            })}
          </div>
          {ds.data.tong > KICH_THUOC_DS_BAI && (
            <Pagination
              style={{ marginTop: 16, textAlign: 'center' }}
              current={trang}
              pageSize={KICH_THUOC_DS_BAI}
              total={ds.data.tong}
              showSizeChanger={false}
              onChange={(t) => doi({ q, ...(t > 1 ? { trang: String(t) } : {}) })}
            />
          )}
        </>
      )}
    </>
  )
}
