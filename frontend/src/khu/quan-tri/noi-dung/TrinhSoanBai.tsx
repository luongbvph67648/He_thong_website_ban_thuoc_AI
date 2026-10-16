import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Drawer, Form, Input, Skeleton, Space, Switch, Tabs } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import { NoiDungMarkdown } from '../../../components/NoiDungMarkdown'
import { NutTaiAnh } from './NutTaiAnh'
import {
  BAI_TRONG,
  GIOI_HAN,
  KHOA_QUERY_NOI_DUNG,
  baiRaSua,
  baiRaTao,
  daDoiNoiDungBai,
  giaTriTuBai,
  gopThayDoi,
  kiemTraBai,
  suaSeVeChoDuyet,
  type BaiVietAdmin,
  type GiaTriBai,
  type LoaiBai,
} from './noiDungWeb'

interface Props {
  loai: LoaiBai
  /** `null` là soạn mới; số là sửa bài đó (nạp đủ nội dung từ máy chủ). */
  baiId: number | null
  onDong: () => void
  onXong: (thongDiep: string) => void
}

/** Trình soạn Markdown (soạn | xem trước) cho bài viết, chính sách, FAQ. Chỉ Admin dùng được. */
export function TrinhSoanBai({ loai, baiId, onDong, onXong }: Props) {
  const chiTiet = useQuery({
    queryKey: [...KHOA_QUERY_NOI_DUNG, 'bai-chi-tiet', baiId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/bai-viet/{bai_viet_id}', { params: { path: { bai_viet_id: baiId as number } } })
      if (error || !data) throw error ?? new Error('Không tải được bài viết')
      return data
    },
    enabled: baiId !== null,
    // `phien_ban` gửi lên PHẢI là bản người soạn đã thấy: làm mới ngầm sẽ cho lưu đè lên người khác mà không báo 409.
    staleTime: Infinity,
    gcTime: 0,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  return (
    <Drawer open title={baiId === null ? 'Soạn bài mới' : 'Sửa bài'} size="large" onClose={onDong} mask={{ closable: false }} destroyOnHidden>
      {baiId !== null && chiTiet.isPending ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : baiId !== null && chiTiet.isError ? (
        <Alert type="error" showIcon title="Không tải được bài viết" action={<Button onClick={() => void chiTiet.refetch()}>Thử lại</Button>} />
      ) : (
        <FormSoan loai={loai} goc={chiTiet.data ?? null} onDong={onDong} onXong={onXong} />
      )}
    </Drawer>
  )
}

function FormSoan({ loai, goc: gocBanDau, onDong, onXong }: { loai: LoaiBai; goc: BaiVietAdmin | null; onDong: () => void; onXong: (m: string) => void }) {
  const { message } = App.useApp()
  const [goc, setGoc] = useState<BaiVietAdmin | null>(gocBanDau)
  const [gia, setGia] = useState<GiaTriBai>(goc ? giaTriTuBai(goc) : BAI_TRONG)
  const [loi, setLoi] = useState<Partial<Record<keyof GiaTriBai, string>>>({})
  const [thongDiep, setThongDiep] = useState<string | null>(null)
  const [dangLuu, setDangLuu] = useState(false)
  const dat = (thayDoi: Partial<GiaTriBai>) => setGia((g) => ({ ...g, ...thayDoi }))

  const veChoDuyet = goc ? suaSeVeChoDuyet(goc.loai, goc.trang_thai, daDoiNoiDungBai(baiRaSua(goc, gia))) : false

  const luu = async () => {
    const sai = kiemTraBai(gia)
    setLoi(sai)
    if (Object.keys(sai).length) return
    setDangLuu(true)
    const kq = goc
      ? await goi(() =>
          api.PATCH('/api/v1/noi-bo/bai-viet/{bai_viet_id}', { params: { path: { bai_viet_id: goc.id } }, body: { phien_ban: goc.phien_ban, ...baiRaSua(goc, gia) } }),
        )
      : await goi(() => api.POST('/api/v1/noi-bo/bai-viet', { body: baiRaTao(loai, gia) }))
    setDangLuu(false)
    if (kq.ok) {
      const sauKhiLuu = kq.data.trang_thai
      const thongDiepXong =
        sauKhiLuu === 'nhap' && kq.data.loai === 'bai_viet' ? 'Đã lưu. Bài đang chờ dược sĩ duyệt mới hiện trên website.' : 'Đã lưu bài viết'
      void message.success(thongDiepXong)
      return onXong(thongDiepXong)
    }
    if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI' && goc) {
      const moi = await goi(() => api.GET('/api/v1/noi-bo/bai-viet/{bai_viet_id}', { params: { path: { bai_viet_id: goc.id } } }))
      if (moi.ok) {
        setGia((g) => gopThayDoi(g, giaTriTuBai(goc), giaTriTuBai(moi.data)))
        setGoc(moi.data)
        return setThongDiep('Bài đã được người khác thay đổi. Form đã cập nhật theo bản mới và giữ phần bạn vừa sửa; kiểm tra rồi lưu lại.')
      }
    }
    if (kq.loi) {
      const theoTruong = loiTheoTruong(kq.loi)
      if (Object.keys(theoTruong).length) setLoi(theoTruong)
    }
    setThongDiep(thongDiepChung(kq.loi))
  }

  return (
    <Form layout="vertical" component="div">
      {thongDiep && <Alert type="warning" showIcon title={thongDiep} style={{ marginBottom: 16 }} />}
      {veChoDuyet && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="Bài đang đăng: sửa nội dung sẽ đưa bài về chờ dược sĩ duyệt và tạm ẩn khỏi website cho tới khi được duyệt lại."
        />
      )}
      {!goc && loai === 'bai_viet' && <Alert type="info" showIcon style={{ marginBottom: 16 }} title="Bài viết sức khỏe cần dược sĩ duyệt mới hiện trên website." />}
      <Form.Item label="Tiêu đề" required htmlFor="bv-tieu-de" validateStatus={loi.tieu_de ? 'error' : undefined} help={loi.tieu_de}>
        <Input id="bv-tieu-de" value={gia.tieu_de} maxLength={GIOI_HAN.tieuDeBai * 2} autoComplete="off" onChange={(e) => dat({ tieu_de: e.target.value })} />
      </Form.Item>
      <Form.Item label="Nội dung (Markdown)" required validateStatus={loi.noi_dung ? 'error' : undefined} help={loi.noi_dung}>
        <Tabs
          items={[
            {
              key: 'soan',
              label: 'Soạn',
              children: (
                <Input.TextArea aria-label="Nội dung" rows={16} value={gia.noi_dung} onChange={(e) => dat({ noi_dung: e.target.value })} placeholder={'## Tiêu đề phụ\n\nĐoạn văn. **Đậm**, [liên kết](/danh-muc/thuoc), - danh sách'} />
              ),
            },
            {
              key: 'xem',
              label: 'Xem trước',
              children: gia.noi_dung.trim() ? <NoiDungMarkdown noiDung={gia.noi_dung} /> : <span style={{ color: 'rgba(0,0,0,.45)' }}>Chưa có nội dung</span>,
            },
          ]}
        />
        <span style={{ color: 'rgba(0,0,0,.45)' }}>
          {gia.noi_dung.length.toLocaleString('vi-VN')}/{GIOI_HAN.noiDungBai.toLocaleString('vi-VN')} ký tự
        </span>
      </Form.Item>
      {loai !== 'faq' && (
        <Form.Item label="Ảnh bìa">
          <NutTaiAnh khu="bai-viet" value={gia.anh_bia_url} onChange={(anh_bia_url) => dat({ anh_bia_url })} loi={loi.anh_bia_url} />
        </Form.Item>
      )}
      <Form.Item label="Đưa vào kho tri thức AI" htmlFor="bv-ai" extra="Chỉ có tác dụng khi bài đã đăng (và đã được dược sĩ duyệt với bài sức khỏe).">
        <Switch id="bv-ai" checked={gia.dua_vao_ai} onChange={(dua_vao_ai) => dat({ dua_vao_ai })} />
      </Form.Item>
      <Space>
        <Button type="primary" loading={dangLuu} onClick={() => void luu()}>
          Lưu
        </Button>
        <Button onClick={onDong}>Hủy</Button>
      </Space>
    </Form>
  )
}
