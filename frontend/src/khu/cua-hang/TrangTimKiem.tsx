import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Empty, Pagination, Skeleton, Typography } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../api/client'
import { layMaPhien } from '../../lib/maPhien'
import { usePhien } from '../../stores/phien'
import { KHOA_QUERY_CUA_HANG, KICH_THUOC_TRANG } from './cuaHang'
import { LuoiSanPham } from './TheSanPham'
import { chuanHoaTuKhoa, duDieuKienTim } from './timKiem'

/** Kết quả tìm kiếm từ khóa (KVL04). Từ khóa và trang nằm trên URL. */
export default function TrangTimKiem() {
  const [tham, datTham] = useSearchParams()
  const q = chuanHoaTuKhoa(tham.get('q'))
  const trang = Math.max(1, Number(tham.get('trang')) || 1)
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const hopLe = duDieuKienTim(q)

  const ketQua = useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'tim-kiem', q, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/tim-kiem', {
        params: { query: { q, trang, kich_thuoc: KICH_THUOC_TRANG }, header: { 'x-ma-phien': layMaPhien() } },
      })
      if (error || !data) throw error ?? new Error('Không tìm kiếm được')
      return data
    },
    // Chờ lấy lại phiên rồi mới tìm: gọi sớm sẽ ghi lịch sử tìm kiếm của khách đã đăng nhập thành của vãng lai.
    enabled: hopLe && daKhoiPhuc,
    refetchOnWindowFocus: false,
    placeholderData: (truoc) => truoc,
  })

  if (!hopLe)
    return (
      <>
        <Typography.Title level={2}>Tìm kiếm</Typography.Title>
        <Empty description={q ? 'Hãy nhập ít nhất 2 ký tự để tìm kiếm' : 'Nhập từ khóa vào ô tìm kiếm ở đầu trang'} />
      </>
    )
  return (
    <>
      <Typography.Title level={2}>
        Kết quả cho “{q}”
      </Typography.Title>
      {ketQua.isError ? (
        <Alert
          type="error"
          showIcon
          title="Không tìm kiếm được"
          action={<Button onClick={() => void ketQua.refetch()}>Thử lại</Button>}
        />
      ) : ketQua.isPending ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : ketQua.data.tong === 0 ? (
        <Empty description="Không tìm thấy sản phẩm phù hợp. Hãy thử từ khóa khác, viết không dấu hoặc tên hoạt chất." />
      ) : ketQua.data.du_lieu.length === 0 ? (
        <Empty description="Trang này không có sản phẩm">
          <Button onClick={() => datTham({ q }, { replace: true })}>Về trang 1</Button>
        </Empty>
      ) : (
        <>
          <Typography.Paragraph type="secondary" role="status">
            {ketQua.data.tong} sản phẩm
          </Typography.Paragraph>
          <LuoiSanPham danhSach={ketQua.data.du_lieu} nguon="tim_kiem" />
          {ketQua.data.tong > KICH_THUOC_TRANG && (
            <Pagination
              style={{ marginTop: 16, textAlign: 'center' }}
              current={trang}
              pageSize={KICH_THUOC_TRANG}
              total={ketQua.data.tong}
              showSizeChanger={false}
              onChange={(t) => {
                datTham(t > 1 ? { q, trang: String(t) } : { q }, { replace: true })
                window.scrollTo?.({ top: 0 })
              }}
            />
          )}
        </>
      )}
    </>
  )
}
