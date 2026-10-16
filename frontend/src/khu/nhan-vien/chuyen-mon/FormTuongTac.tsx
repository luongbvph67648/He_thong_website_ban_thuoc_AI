import { Alert, Form, Input, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { ChonDuLieuChung } from '../../../components/ChonDuLieuChung'
import { NhanTrangThai } from '../../../components/NhanTrangThai'
import { nhanTrangThai } from '../../../lib/trangThai'
import { giaTriTuBanGhi, kiemTraTuongTac, MUC_DO, TUONG_TAC_TRONG, type GiaTriTuongTac, type LoiTuongTac, type TuongTac } from './tuongTac'

interface Props {
  /** `null` là đóng. */
  mo: { kieu: 'tao' } | { kieu: 'sua'; ban: TuongTac } | null
  dangLuu: boolean
  /** Trả `null` nếu lưu được; trả lỗi theo ô (đã đổi sang tên ô của form) và/hoặc thông điệp chung nếu không. */
  onLuu: (g: GiaTriTuongTac) => Promise<{ theoO: LoiTuongTac; chung: string | null } | null>
  onDong: () => void
}

function O({ nhan, id, loi, children }: { nhan: string; id: string; loi?: string; children: React.ReactNode }) {
  return (
    <Form.Item label={nhan} htmlFor={id} validateStatus={loi ? 'error' : undefined} help={loi}>
      {children}
    </Form.Item>
  )
}

/** Hộp thoại thêm/sửa một tương tác. Sửa thì cặp hoạt chất cố định (khóa chính), chỉ đổi mức độ và nội dung. */
export function FormTuongTac({ mo, dangLuu, onLuu, onDong }: Props) {
  const [g, setG] = useState<GiaTriTuongTac>(TUONG_TAC_TRONG)
  const [daThuLuu, setDaThuLuu] = useState(false)
  const [loiMayChu, setLoiMayChu] = useState<LoiTuongTac>({})
  const [chung, setChung] = useState<string | null>(null)

  // Điền giá trị ban đầu CHỈ khi hộp thoại mở (hoặc chuyển sang bản ghi khác), không phụ thuộc đối tượng dựng mới mỗi lần render.
  const khoaMo = mo === null ? null : mo.kieu === 'sua' ? `sua-${mo.ban.hoat_chat_a_id}-${mo.ban.hoat_chat_b_id}` : 'tao'
  useEffect(() => {
    if (!mo) return
    setG(mo.kieu === 'sua' ? giaTriTuBanGhi(mo.ban) : TUONG_TAC_TRONG)
    setDaThuLuu(false)
    setLoiMayChu({})
    setChung(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [khoaMo])

  const sua = mo?.kieu === 'sua'
  const loi: LoiTuongTac = { ...(daThuLuu ? kiemTraTuongTac(g) : {}), ...loiMayChu }
  const doi = (thayDoi: Partial<GiaTriTuongTac>) => {
    setG({ ...g, ...thayDoi })
    setLoiMayChu((cu) => {
      const con = { ...cu }
      for (const k of Object.keys(thayDoi) as (keyof GiaTriTuongTac)[]) delete con[k]
      return con
    })
  }

  const luu = async () => {
    setDaThuLuu(true)
    setChung(null)
    if (Object.keys(kiemTraTuongTac(g)).length > 0) return
    const ketQua = await onLuu(g)
    if (!ketQua) return
    setLoiMayChu(ketQua.theoO)
    setChung(ketQua.chung)
  }

  return (
    <Modal
      title={sua ? 'Sửa tương tác' : 'Thêm tương tác giữa hai hoạt chất'}
      open={mo !== null}
      okText={sua ? 'Lưu' : 'Thêm'}
      cancelText="Hủy"
      confirmLoading={dangLuu}
      onOk={() => void luu()}
      onCancel={onDong}
      destroyOnHidden
      forceRender
      width={640}
    >
      <Form layout="vertical" component="div">
        {chung && <Alert type="error" showIcon title={chung} style={{ marginBottom: 16 }} />}
        <O nhan="Hoạt chất thứ nhất" id="tt-hoat-chat-1" loi={loi.hoat_chat_1}>
          <ChonDuLieuChung ma="hoat-chat" batBuoc id="tt-hoat-chat-1" nhan="Hoạt chất thứ nhất" placeholder="Chọn hoạt chất" disabled={sua} value={g.hoat_chat_1} onChange={(v) => doi({ hoat_chat_1: v })} />
        </O>
        <O nhan="Hoạt chất thứ hai" id="tt-hoat-chat-2" loi={loi.hoat_chat_2}>
          <ChonDuLieuChung ma="hoat-chat" batBuoc id="tt-hoat-chat-2" nhan="Hoạt chất thứ hai" placeholder="Chọn hoạt chất" disabled={sua} value={g.hoat_chat_2} onChange={(v) => doi({ hoat_chat_2: v })} />
        </O>
        <O nhan="Mức độ" id="tt-muc-do" loi={loi.muc_do}>
          <Select
            id="tt-muc-do"
            placeholder="Chọn mức độ"
            value={g.muc_do}
            status={loi.muc_do ? 'error' : undefined}
            options={MUC_DO.map((m) => ({ value: m, label: nhanTrangThai('muc_do_tuong_tac', m).nhan }))}
            onChange={(v) => doi({ muc_do: v })}
          />
        </O>
        {g.muc_do && (
          <div style={{ marginBottom: 16 }}>
            <NhanTrangThai loai="muc_do_tuong_tac" giaTri={g.muc_do} />
          </div>
        )}
        <O nhan="Khuyến cáo cho người dùng" id="tt-khuyen-cao" loi={loi.khuyen_cao}>
          <Input.TextArea id="tt-khuyen-cao" autoSize={{ minRows: 3, maxRows: 8 }} value={g.khuyen_cao} status={loi.khuyen_cao ? 'error' : undefined} onChange={(e) => doi({ khuyen_cao: e.target.value })} />
        </O>
        <O nhan="Cơ chế (không bắt buộc)" id="tt-co-che" loi={loi.co_che}>
          <Input.TextArea id="tt-co-che" autoSize={{ minRows: 2, maxRows: 8 }} value={g.co_che} status={loi.co_che ? 'error' : undefined} onChange={(e) => doi({ co_che: e.target.value })} />
        </O>
        <O nhan="Nguồn tham khảo (không bắt buộc)" id="tt-nguon" loi={loi.nguon_tham_khao}>
          <Input id="tt-nguon" autoComplete="off" value={g.nguon_tham_khao} status={loi.nguon_tham_khao ? 'error' : undefined} onChange={(e) => doi({ nguon_tham_khao: e.target.value })} />
        </O>
      </Form>
    </Modal>
  )
}
