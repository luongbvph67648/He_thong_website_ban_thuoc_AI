import { Form, Input, Modal } from 'antd'
import { useEffect } from 'react'
import { loiTheoTruong, type LoiApi } from '../../../api/loi'
import { loiDuongDan, loiTen, loiVanBan } from '../../../lib/duLieuChung'
import type { BanGhi, CauHinhNhom, GiaTriForm, TruongForm } from './nhom'

interface Props {
  nhom: CauHinhNhom
  /** `null` là đóng; `{ ban: null }` là thêm mới, có `ban` là sửa. */
  mo: { ban: BanGhi | null } | null
  dangLuu: boolean
  /** Trả `null` nếu lưu được; trả lỗi API để form gắn vào từng ô. */
  onLuu: (giaTri: GiaTriForm) => Promise<LoiApi | null>
  onDong: () => void
}

function kiemTra(t: TruongForm, v: string): string | null {
  if (t.loai === 'ten') return loiTen(v, t.toiDa)
  if (t.loai === 'url') return loiDuongDan(v)
  return loiVanBan(v, t.toiDa, t.loai === 'nhieu_dong')
}

/** Hộp thoại thêm/sửa một bản ghi của nhóm; ô nhập dựng từ `nhom.truong`. */
export function FormDuLieuChung({ nhom, mo, dangLuu, onLuu, onDong }: Props) {
  const [form] = Form.useForm<GiaTriForm>()

  useEffect(() => {
    if (!mo) return
    form.setFieldsValue(Object.fromEntries(nhom.truong.map((t) => [t.ten, String(mo.ban?.[t.ten] ?? '')])))
  }, [mo, nhom, form])

  const gui = async (giaTri: GiaTriForm) => {
    const loi = await onLuu(giaTri)
    if (!loi) return
    const theoTruong = loiTheoTruong(loi)
    if (Object.keys(theoTruong).length > 0) {
      form.setFields(Object.entries(theoTruong).map(([name, thongDiep]) => ({ name, errors: [thongDiep] })))
    }
  }

  return (
    <Modal
      title={mo?.ban ? `Sửa ${nhom.danhTu}` : `Thêm ${nhom.danhTu}`}
      open={mo !== null}
      okText={mo?.ban ? 'Lưu' : 'Thêm'}
      cancelText="Hủy"
      confirmLoading={dangLuu}
      onOk={() => form.submit()}
      onCancel={onDong}
      destroyOnHidden
      forceRender
    >
      <Form<GiaTriForm> form={form} layout="vertical" onFinish={gui} initialValues={Object.fromEntries(nhom.truong.map((t) => [t.ten, '']))}>
        {nhom.truong.map((t) => (
          <Form.Item
            key={t.ten}
            label={t.nhan}
            name={t.ten}
            extra={t.loai === 'url' ? 'Bắt đầu bằng / hoặc http(s)://' : undefined}
            rules={[
              {
                validator: async (_, v: string) => {
                  const loi = kiemTra(t, v ?? '')
                  if (loi) throw new Error(loi)
                },
              },
            ]}
          >
            {t.loai === 'nhieu_dong' ? <Input.TextArea rows={4} autoComplete="off" /> : <Input autoComplete="off" />}
          </Form.Item>
        ))}
      </Form>
    </Modal>
  )
}
