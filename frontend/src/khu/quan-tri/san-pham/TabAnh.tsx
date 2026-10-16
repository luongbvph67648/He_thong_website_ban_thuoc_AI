import { ArrowDownOutlined, ArrowUpOutlined, DeleteOutlined, StarFilled, StarOutlined, UploadOutlined } from '@ant-design/icons'
import { useMutation } from '@tanstack/react-query'
import { Alert, App, Button, Popconfirm, Space, Tag } from 'antd'
import { useRef, useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung, type KetQuaGoi } from '../../../api/goi'
import { ANH_TOI_DA, KIEU_ANH, loiTepAnh } from './anh'
import { type SanPhamChiTiet } from './sanPham'

interface Props {
  ban: SanPhamChiTiet
  coQuyenGhi: boolean
  capNhat: (ban: SanPhamChiTiet) => void
  lamMoi: () => Promise<unknown>
}

/**
 * Tab "Ảnh": mỗi thao tác là một lần gọi máy chủ riêng (kèm `phien_ban` đã thấy) và trả về cả sản phẩm, nên danh sách
 * ảnh luôn lấy từ bản mới nhất chứ không giữ trạng thái cục bộ.
 */
export function TabAnh({ ban, coQuyenGhi, capNhat, lamMoi }: Props) {
  const { message } = App.useApp()
  const oChonTep = useRef<HTMLInputElement>(null)
  const [thongDiep, setThongDiep] = useState<string | null>(null)
  const anh = ban.anh
  const duongDan = { path: { san_pham_id: ban.id } }

  const chay = useMutation({ mutationFn: (thucHien: () => Promise<KetQuaGoi<SanPhamChiTiet>>) => thucHien() })
  const thaoTac = async (thanhCong: string, thucHien: () => Promise<KetQuaGoi<SanPhamChiTiet>>) => {
    setThongDiep(null)
    const kq = await chay.mutateAsync(thucHien)
    if (!kq.ok) {
      if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') {
        await lamMoi()
        return setThongDiep('Sản phẩm vừa được người khác thay đổi. Đã tải bản mới, hãy thử lại thao tác.')
      }
      return setThongDiep(thongDiepChung(kq.loi))
    }
    capNhat(kq.data)
    void message.success(thanhCong)
  }

  const chonTep = (tep: File | undefined) => {
    if (oChonTep.current) oChonTep.current.value = '' // cho phép chọn lại đúng tệp vừa bị từ chối
    if (!tep) return
    const loi = loiTepAnh(tep)
    if (loi) return setThongDiep(`${tep.name}: ${loi}`)
    void thaoTac('Đã tải ảnh lên', () =>
      goi(() =>
        api.POST('/api/v1/noi-bo/san-pham/{san_pham_id}/anh', {
          params: { ...duongDan, query: { phien_ban: ban.phien_ban } },
          body: { tep: '' },
          // Gửi multipart: trình duyệt tự đặt Content-Type kèm boundary khi thân là FormData.
          bodySerializer: () => {
            const form = new FormData()
            form.append('tep', tep)
            return form
          },
        }),
      ),
    )
  }

  const doiViTri = (i: number, huong: -1 | 1) => {
    const ids = anh.map((a) => a.id)
    ;[ids[i], ids[i + huong]] = [ids[i + huong], ids[i]]
    void thaoTac('Đã đổi thứ tự ảnh', () => goi(() => api.PUT('/api/v1/noi-bo/san-pham/{san_pham_id}/anh/thu-tu', { params: duongDan, body: { phien_ban: ban.phien_ban, ids } })))
  }

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      {thongDiep && <Alert type="error" showIcon title={thongDiep} closable={{ onClose: () => setThongDiep(null) }} />}
      {coQuyenGhi && (
        <Space align="center" wrap>
          <input ref={oChonTep} type="file" accept={KIEU_ANH.join(',')} hidden aria-label="Chọn ảnh để tải lên" onChange={(e) => chonTep(e.target.files?.[0])} />
          <Button icon={<UploadOutlined />} loading={chay.isPending} disabled={anh.length >= ANH_TOI_DA} onClick={() => oChonTep.current?.click()}>
            Tải ảnh lên
          </Button>
          <span style={{ color: 'rgba(0,0,0,.45)' }}>
            JPEG, PNG hoặc WebP, tối đa 5 MB mỗi ảnh; {anh.length}/{ANH_TOI_DA} ảnh. Ảnh đầu tiên là ảnh chính.
          </span>
        </Space>
      )}
      {anh.length === 0 ? (
        <Alert type="info" showIcon title="Sản phẩm chưa có ảnh." />
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
          {anh.map((a, i) => (
            <li key={a.id} style={{ border: '1px solid rgba(0,0,0,.12)', borderRadius: 8, padding: 8 }}>
              <img src={a.url} alt={`Ảnh ${i + 1} của ${ban.ten}`} style={{ width: '100%', aspectRatio: '1 / 1', objectFit: 'cover', borderRadius: 4 }} />
              <Space size={4} wrap style={{ marginTop: 8 }}>
                {a.la_anh_chinh ? (
                  <Tag color="gold" icon={<StarFilled />}>
                    Ảnh chính
                  </Tag>
                ) : (
                  coQuyenGhi && (
                    <Button size="small" icon={<StarOutlined />} loading={chay.isPending} aria-label={`Đặt ảnh ${i + 1} làm ảnh chính`} onClick={() => void thaoTac('Đã đổi ảnh chính', () => goi(() => api.PUT('/api/v1/noi-bo/san-pham/{san_pham_id}/anh/{anh_id}/chinh', { params: { path: { ...duongDan.path, anh_id: a.id } }, body: { phien_ban: ban.phien_ban } })))}>
                      Đặt làm ảnh chính
                    </Button>
                  )
                )}
                {coQuyenGhi && (
                  <>
                    <Button size="small" icon={<ArrowUpOutlined />} disabled={i === 0 || chay.isPending} aria-label={`Chuyển ảnh ${i + 1} lên`} onClick={() => doiViTri(i, -1)} />
                    <Button size="small" icon={<ArrowDownOutlined />} disabled={i === anh.length - 1 || chay.isPending} aria-label={`Chuyển ảnh ${i + 1} xuống`} onClick={() => doiViTri(i, 1)} />
                    <Popconfirm
                      title="Xóa ảnh này?"
                      description="Ảnh bị xóa khỏi sản phẩm và khỏi bộ nhớ."
                      okText="Xóa"
                      cancelText="Hủy"
                      okButtonProps={{ danger: true }}
                      onConfirm={() => thaoTac('Đã xóa ảnh', () => goi(() => api.DELETE('/api/v1/noi-bo/san-pham/{san_pham_id}/anh/{anh_id}', { params: { path: { ...duongDan.path, anh_id: a.id }, query: { phien_ban: ban.phien_ban } } })))}
                    >
                      <Button size="small" danger icon={<DeleteOutlined />} disabled={chay.isPending} aria-label={`Xóa ảnh ${i + 1}`} />
                    </Popconfirm>
                  </>
                )}
              </Space>
            </li>
          ))}
        </ul>
      )}
    </Space>
  )
}
