import { Form, Input, Modal, Switch } from 'antd'
import { useEffect } from 'react'
import { loiTheoTruong, type LoiApi } from '../../../api/loi'
import { chuoiHoacNull, gonTen, loiDuongDan, loiTen } from '../../../lib/duLieuChung'

export const TEN_TOI_DA = 150

export interface GiaTriFormDanhMuc {
  ten: string
  anh_url: string | null
  dang_hien_thi: boolean
}

interface Props {
  /** `null` là đóng. */
  mo: { kieu: 'tao'; chaTen: string | null } | { kieu: 'sua'; ban: GiaTriFormDanhMuc & { id: number } } | null
  dangLuu: boolean
  /** Trả `null` nếu lưu được; trả lỗi API để form gắn vào từng ô. */
  onLuu: (giaTri: GiaTriFormDanhMuc) => Promise<LoiApi | null>
  onDong: () => void
}

interface DuLieuForm {
  ten: string
  anh_url?: string
  dang_hien_thi: boolean
}

/** Hộp thoại thêm/sửa một danh mục. Chuyển cha và sắp xếp làm bằng kéo thả, không có ở đây. */
export function FormDanhMuc({ mo, dangLuu, onLuu, onDong }: Props) {
  const [form] = Form.useForm<DuLieuForm>()

  useEffect(() => {
    if (!mo) return
    form.setFieldsValue(
      mo.kieu === 'sua'
        ? { ten: mo.ban.ten, anh_url: mo.ban.anh_url ?? '', dang_hien_thi: mo.ban.dang_hien_thi }
        : { ten: '', anh_url: '', dang_hien_thi: true },
    )
  }, [mo, form])

  const gui = async (giaTri: DuLieuForm) => {
    const loi = await onLuu({ ten: gonTen(giaTri.ten), anh_url: chuoiHoacNull(giaTri.anh_url), dang_hien_thi: giaTri.dang_hien_thi })
    if (!loi) return
    const theoTruong = loiTheoTruong(loi)
    if (Object.keys(theoTruong).length > 0) {
      form.setFields(Object.entries(theoTruong).map(([name, thongDiep]) => ({ name: name as keyof DuLieuForm, errors: [thongDiep] })))
    }
  }

  return (
    <Modal
      title={mo?.kieu === 'sua' ? 'Sửa danh mục' : mo?.chaTen ? `Thêm danh mục con của “${mo.chaTen}”` : 'Thêm danh mục gốc'}
      open={mo !== null}
      okText={mo?.kieu === 'sua' ? 'Lưu' : 'Thêm'}
      cancelText="Hủy"
      confirmLoading={dangLuu}
      onOk={() => form.submit()}
      onCancel={onDong}
      destroyOnHidden
      forceRender
    >
      <Form<DuLieuForm> form={form} layout="vertical" onFinish={gui} initialValues={{ ten: '', anh_url: '', dang_hien_thi: true }}>
        <Form.Item
          label="Tên danh mục"
          name="ten"
          rules={[{ validator: async (_, v: string) => { const loi = loiTen(v ?? '', TEN_TOI_DA); if (loi) throw new Error(loi) } }]}
        >
          <Input maxLength={TEN_TOI_DA * 2} autoComplete="off" />
        </Form.Item>
        <Form.Item
          label="Đường dẫn ảnh (không bắt buộc)"
          name="anh_url"
          extra="Bắt đầu bằng / hoặc http(s)://"
          rules={[{ validator: async (_, v: string) => { const loi = loiDuongDan(v ?? ''); if (loi) throw new Error(loi) } }]}
        >
          <Input autoComplete="off" />
        </Form.Item>
        <Form.Item label="Hiển thị trên cửa hàng" name="dang_hien_thi" valuePropName="checked" extra="Tắt để ẩn danh mục này và mọi danh mục con khỏi khách; bật lại bất cứ lúc nào.">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  )
}
