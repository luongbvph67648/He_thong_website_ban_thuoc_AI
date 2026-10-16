import { ArrowLeftOutlined, DeleteOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Popconfirm, Result, Space, Spin, Tabs, Typography } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { laLoiApi } from '../../../api/loi'
import { NhanTrangThai } from '../../../components/NhanTrangThai'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'
import { KHOA_QUERY_SAN_PHAM, khoaChiTiet, THONG_DIEP_XUNG_DOT, type SanPhamChiTiet } from './sanPham'
import { TabAnh } from './TabAnh'
import { TabDonVi } from './TabDonVi'
import { TabThanhPhan } from './TabThanhPhan'
import { TabThongTin } from './TabThongTin'
import { useCayDanhMuc } from './useCayDanhMuc'

export function KhongTimThay() {
  return (
    <Result
      status="404"
      title="Không tìm thấy sản phẩm"
      subTitle="Sản phẩm không tồn tại hoặc đã bị xóa."
      extra={
        <Link to=".." relative="path">
          <Button type="primary">Về danh sách sản phẩm</Button>
        </Link>
      }
    />
  )
}

/** Xem và sửa một sản phẩm (AD04) theo bốn tab; mỗi tab lưu độc lập bằng một lời gọi riêng. */
export default function SuaSanPham({ id }: { id: number }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const dieuHuong = useNavigate()
  const coGhi = coQuyen(usePhien((s) => s.quyen), 'product.commercial.manage')
  const { tuyChon } = useCayDanhMuc()

  // Không tự làm mới (focus, kết nối lại, quá hạn): `phien_ban` phải là bản người dùng đã thấy, nếu không bản đã sửa dở
  // sẽ được lưu đè lên thay đổi của người khác mà không báo xung đột. Dữ liệu chỉ đổi sau khi mình ghi hoặc gặp 409.
  const chiTiet = useQuery({
    queryKey: khoaChiTiet(id),
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/san-pham/{san_pham_id}', { params: { path: { san_pham_id: id } } })
      if (error) throw error
      return data
    },
    staleTime: Infinity,
    gcTime: 0,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  const capNhat = (ban: SanPhamChiTiet) => {
    queryClient.setQueryData(khoaChiTiet(id), ban)
    void queryClient.invalidateQueries({ queryKey: [...KHOA_QUERY_SAN_PHAM, 'danh-sach'] })
  }
  // Trả bản mới, hoặc `undefined` nếu tải lại lỗi (khi đó `refetch` vẫn giữ bản cũ trong `data`, không được tưởng là mới).
  const lamMoi = async (): Promise<SanPhamChiTiet | undefined> => {
    const kq = await chiTiet.refetch()
    return kq.isError ? undefined : kq.data
  }

  const xoa = useMutation({
    mutationFn: (phienBan: string) =>
      goi(() => api.DELETE('/api/v1/noi-bo/san-pham/{san_pham_id}', { params: { path: { san_pham_id: id }, query: { phien_ban: phienBan } } })),
  })

  if (chiTiet.isError && laLoiApi(chiTiet.error) && chiTiet.error.ma_loi === 'KHONG_TIM_THAY') return <KhongTimThay />
  // Tải lại lỗi mà vẫn còn bản cũ (`data`) thì giữ nguyên trang: thay bằng cảnh báo là mất chữ người dùng đang gõ.
  if (chiTiet.isError && !chiTiet.data) return <Alert type="error" showIcon title="Không tải được sản phẩm" />
  const ban = chiTiet.data
  if (!ban) return <Spin style={{ display: 'block', margin: '48px auto' }} />

  const xoaSanPham = async () => {
    const kq = await xoa.mutateAsync(ban.phien_ban)
    if (!kq.ok) {
      if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') {
        await lamMoi()
        return void message.error(THONG_DIEP_XUNG_DOT)
      }
      return void message.error(thongDiepChung(kq.loi))
    }
    void message.success(`Đã xóa “${ban.ten}”`)
    await queryClient.invalidateQueries({ queryKey: [...KHOA_QUERY_SAN_PHAM, 'danh-sach'] })
    queryClient.removeQueries({ queryKey: khoaChiTiet(id) })
    dieuHuong('..', { relative: 'path', replace: true })
  }

  return (
    <div>
      <Link to=".." relative="path">
        <Button type="link" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0 }}>
          Danh sách sản phẩm
        </Button>
      </Link>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }} align="start" wrap>
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>
            {ban.ten}
          </Typography.Title>
          <Space size={8} wrap style={{ marginTop: 4 }}>
            <code>{ban.sku}</code>
            <NhanTrangThai loai="loai_san_pham" giaTri={ban.loai_san_pham} />
            <NhanTrangThai loai="kinh_doanh" giaTri={ban.trang_thai} />
          </Space>
        </div>
        <YeuCauQuyen ma="product.commercial.manage" kieu="nut">
          <Popconfirm
            title="Xóa sản phẩm này?"
            description="Sản phẩm biến mất khỏi cửa hàng và danh sách; lịch sử đơn hàng vẫn giữ. Chỉ xóa được khi không còn hàng tồn, đang giữ hay biệt trữ. Muốn tạm ngừng bán thì đổi trạng thái sang Ngừng kinh doanh."
            okText="Xóa sản phẩm"
            cancelText="Hủy"
            okButtonProps={{ danger: true }}
            onConfirm={() => xoaSanPham()}
          >
            <Button danger icon={<DeleteOutlined />} loading={xoa.isPending}>
              Xóa sản phẩm
            </Button>
          </Popconfirm>
        </YeuCauQuyen>
      </Space>
      <Tabs
        items={[
          { key: 'thong-tin', label: 'Thông tin', children: <TabThongTin key={ban.id} ban={ban} cay={tuyChon} coQuyenGhi={coGhi} capNhat={capNhat} lamMoi={lamMoi} /> },
          { key: 'don-vi', label: 'Đơn vị và giá', children: <TabDonVi key={ban.id} ban={ban} coQuyenGhi={coGhi} capNhat={capNhat} lamMoi={lamMoi} /> },
          { key: 'thanh-phan', label: 'Thành phần', children: <TabThanhPhan key={ban.id} ban={ban} coQuyenGhi={coGhi} capNhat={capNhat} lamMoi={lamMoi} /> },
          { key: 'anh', label: `Ảnh (${ban.anh.length})`, children: <TabAnh ban={ban} coQuyenGhi={coGhi} capNhat={capNhat} lamMoi={lamMoi} /> },
        ]}
      />
    </div>
  )
}
