import { BellOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Empty, Popover, Skeleton, Typography } from 'antd'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { dinhDangNgay } from '../lib/dinhDang'

const CHU_KY_CAP_NHAT_MS = 60_000
const SO_THONG_BAO_HIEN = 10

/** `lien_ket` do máy chủ gửi; chỉ điều hướng khi là đường dẫn nội bộ (không bao giờ nhảy sang URL ngoài). */
function laDuongDanNoiBo(lienKet: string | null): lienKet is string {
  return !!lienKet && lienKet.startsWith('/') && !lienKet.startsWith('//') && !lienKet.includes('\\')
}

/** Chuông thông báo của nhân viên (NV02): số chưa đọc cập nhật mỗi phút, mở ra xem 10 thông báo mới nhất. */
export function ChuongThongBao({ phamVi = 'noi_bo' }: { phamVi?: 'noi_bo' | 'khach' }) {
  const goc = phamVi === 'khach' ? 'toi' : 'noi-bo'
  const KHOA_DEM = [goc, 'thong-bao', 'so-chua-doc'] as const
  const KHOA_DANH_SACH = [goc, 'thong-bao', 'danh-sach'] as const
  const [mo, setMo] = useState(false)
  const dieuHuong = useNavigate()
  const queryClient = useQueryClient()

  const dem = useQuery({
    queryKey: KHOA_DEM,
    refetchInterval: CHU_KY_CAP_NHAT_MS,
    queryFn: async () => {
      const { data, error } = phamVi === 'khach' ? await api.GET('/api/v1/toi/thong-bao/so-chua-doc') : await api.GET('/api/v1/noi-bo/thong-bao/so-chua-doc')
      if (error) throw error
      return data.so_chua_doc
    },
  })
  const danhSach = useQuery({
    queryKey: KHOA_DANH_SACH,
    enabled: mo,
    queryFn: async () => {
      const query = { params: { query: { kich_thuoc: SO_THONG_BAO_HIEN } } }
      const { data, error } = phamVi === 'khach' ? await api.GET('/api/v1/toi/thong-bao', query) : await api.GET('/api/v1/noi-bo/thong-bao', query)
      if (error) throw error
      return data.du_lieu
    },
  })

  const lamMoi = () => queryClient.invalidateQueries({ queryKey: [goc, 'thong-bao'] })
  const daDoc = useMutation({
    mutationFn: async (id: number) => {
      const p = { params: { path: { thong_bao_id: id } } }
      const { error } = phamVi === 'khach' ? await api.POST('/api/v1/toi/thong-bao/{thong_bao_id}/da-doc', p) : await api.POST('/api/v1/noi-bo/thong-bao/{thong_bao_id}/da-doc', p)
      if (error) throw error
    },
    onSettled: lamMoi,
  })
  const daDocTatCa = useMutation({
    mutationFn: async () => {
      const { error } = phamVi === 'khach' ? await api.POST('/api/v1/toi/thong-bao/da-doc-tat-ca') : await api.POST('/api/v1/noi-bo/thong-bao/da-doc-tat-ca')
      if (error) throw error
    },
    onSettled: lamMoi,
  })

  const soChuaDoc = dem.data ?? 0
  const noiDung = (
    <div style={{ width: 340 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Typography.Text strong>Thông báo</Typography.Text>
        <Button type="link" size="small" disabled={soChuaDoc === 0 || daDocTatCa.isPending} onClick={() => daDocTatCa.mutate()}>
          Đánh dấu tất cả đã đọc
        </Button>
      </div>
      {phamVi === 'khach' && <div style={{ marginBottom: 8 }}><Link to="/tai-khoan/thong-bao" onClick={() => setMo(false)}>Xem tất cả</Link></div>}
      {danhSach.isPending ? (
        <Skeleton active paragraph={{ rows: 3 }} />
      ) : danhSach.isError ? (
        <Typography.Text type="danger">Không tải được thông báo, vui lòng thử lại.</Typography.Text>
      ) : danhSach.data.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chưa có thông báo" />
      ) : (
        <div role="list" style={{ maxHeight: 360, overflowY: 'auto' }}>
          {danhSach.data.map((tb) => (
            // Dùng <button> để thao tác được bằng bàn phím; nền xanh nhạt đánh dấu thông báo chưa đọc.
            <button
              key={tb.id}
              type="button"
              role="listitem"
              onClick={() => {
                if (!tb.da_doc) daDoc.mutate(tb.id)
                if (laDuongDanNoiBo(tb.lien_ket)) {
                  setMo(false)
                  dieuHuong(tb.lien_ket)
                }
              }}
              style={{
                display: 'block',
                width: '100%',
                textAlign: 'left',
                border: 0,
                borderBottom: '1px solid #f0f0f0',
                padding: '8px 4px',
                cursor: 'pointer',
                background: tb.da_doc ? 'transparent' : '#f6ffed',
                font: 'inherit',
              }}
            >
              <div>
                <Typography.Text strong={!tb.da_doc}>{tb.tieu_de}</Typography.Text>
              </div>
              {tb.noi_dung && <div>{tb.noi_dung}</div>}
              <div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {dinhDangNgay(tb.created_at, 'ngayGio')}
                </Typography.Text>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )

  return (
    <Popover content={noiDung} trigger="click" placement="bottomRight" open={mo} onOpenChange={setMo}>
      <Button type="text" aria-label={soChuaDoc > 0 ? `Thông báo, ${soChuaDoc} chưa đọc` : 'Thông báo'}>
        <Badge count={soChuaDoc} overflowCount={99} size="small">
          <BellOutlined style={{ fontSize: 18 }} />
        </Badge>
      </Button>
    </Popover>
  )
}
