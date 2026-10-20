import { AudioOutlined, CameraOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { AutoComplete, Button, Input, Tag, Tooltip, message } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { KHOA_QUERY_CUA_HANG } from './cuaHang'
import { chuanHoaTuKhoa, duDieuKienTim, duongDanGoiY, duongDanTimKiem, TRE_GOI_Y_MS, type GoiY } from './timKiem'

const KHOA_GOI_Y = /^(san_pham|hoat_chat):\d+$/

type KetQuaGiongNoi = { results: ArrayLike<ArrayLike<{ transcript: string }>> }
type NhanDangGiongNoi = {
  lang: string
  onresult: ((event: KetQuaGiongNoi) => void) | null
  onend: (() => void) | null
  onerror: (() => void) | null
  start: () => void
  stop: () => void
}

/** Ô tìm kiếm ở header: gợi ý khi gõ (trễ 250 ms, từ 2 ký tự); Enter hoặc nút tìm chạy tìm kiếm đầy đủ. */
export function OTimKiem() {
  const [go, datGo] = useState('')
  const [daTre, datDaTre] = useState('')
  const [dangNghe, datDangNghe] = useState(false)
  const dieuHuong = useNavigate()
  const choTim = useRef<ReturnType<typeof setTimeout> | null>(null)
  const nhanDang = useRef<NhanDangGiongNoi | null>(null)

  useEffect(() => {
    const h = setTimeout(() => datDaTre(chuanHoaTuKhoa(go)), TRE_GOI_Y_MS)
    return () => clearTimeout(h)
  }, [go])

  const goiY = useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'goi-y', daTre],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/tim-kiem/goi-y', { params: { query: { q: daTre } } })
      if (error || !data) throw new Error('Không tải được gợi ý')
      return data
    },
    enabled: duDieuKienTim(daTre),
    staleTime: 60_000,
    placeholderData: (truoc) => truoc, // gõ tiếp thì giữ danh sách cũ tới khi có danh sách mới, không nháy trống
  })
  const danhSach: GoiY[] = duDieuKienTim(daTre) ? (goiY.data ?? []) : []

  useEffect(() => () => {
    if (choTim.current) clearTimeout(choTim.current)
    nhanDang.current?.stop()
  }, [])

  // Nhấn Enter khi đang tô sáng một gợi ý làm cả `onSelect` lẫn `onSearch` chạy (thứ tự tùy trình duyệt): hoãn tìm đầy đủ
  // một nhịp để `onSelect` hủy nó, nếu không khách bị đưa tới trang kết quả thay vì sản phẩm đã chọn.
  const timDayDu = (q: string) => {
    if (!duDieuKienTim(q)) return
    if (choTim.current) clearTimeout(choTim.current)
    choTim.current = setTimeout(() => dieuHuong(duongDanTimKiem(q)), 0)
  }

  const batDauTimBangGiongNoi = () => {
    const cuaSo = window as Window & {
      SpeechRecognition?: new () => NhanDangGiongNoi
      webkitSpeechRecognition?: new () => NhanDangGiongNoi
    }
    const BoNhanDang = cuaSo.SpeechRecognition ?? cuaSo.webkitSpeechRecognition
    if (!BoNhanDang) {
      void message.info('Trình duyệt này chưa hỗ trợ tìm kiếm bằng giọng nói.')
      return
    }
    nhanDang.current?.stop()
    const boNhanDang = new BoNhanDang()
    boNhanDang.lang = 'vi-VN'
    boNhanDang.onresult = (event) => {
      const tuKhoa = event.results[0]?.[0]?.transcript?.trim()
      if (tuKhoa) {
        datGo(tuKhoa)
        timDayDu(tuKhoa)
      }
    }
    boNhanDang.onend = () => datDangNghe(false)
    boNhanDang.onerror = () => datDangNghe(false)
    nhanDang.current = boNhanDang
    datDangNghe(true)
    boNhanDang.start()
  }

  return (
    <div className="tim-kiem-header">
    <AutoComplete
      className="tim-kiem-goi-y"
      value={go}
      onChange={(v) => {
        // Chọn một gợi ý cũng phát `onChange` với giá trị của gợi ý đó (khóa nội bộ): bỏ qua, ô vẫn giữ chữ người dùng gõ.
        if (!KHOA_GOI_Y.test(v)) datGo(v)
      }}
      popupMatchSelectWidth
      options={danhSach.map((g, i) => ({
        // Giá trị phải duy nhất (sản phẩm và hoạt chất có thể trùng tên): dùng khóa nội bộ, đích đi theo `goiY`.
        value: `${g.kieu}:${i}`,
        key: `${g.kieu}-${i}`,
        goiY: g,
        label: (
          <span>
            {g.ten} {g.kieu === 'hoat_chat' && <Tag>Hoạt chất</Tag>}
            {g.can_tu_van && <Tag color="volcano">Cần tư vấn</Tag>}
          </span>
        ),
      }))}
      onSelect={(_, opt) => {
        if (choTim.current) clearTimeout(choTim.current)
        const g = (opt as { goiY: GoiY }).goiY
        datGo(g.ten)
        dieuHuong(duongDanGoiY(g))
      }}
    >
      <Input
        placeholder="Tìm thuốc, thực phẩm chức năng, thiết bị y tế..."
        aria-label="Tìm kiếm"
        allowClear
        maxLength={100}
        onPressEnter={(event) => timDayDu(event.currentTarget.value)}
      />
    </AutoComplete>
    <div className="tim-kiem-cong-cu">
      <Tooltip title={dangNghe ? 'Đang nghe...' : 'Tìm kiếm bằng giọng nói'}>
        <Button className={dangNghe ? 'dang-nghe' : ''} type="text" icon={<AudioOutlined />} aria-label="Tìm kiếm bằng giọng nói" onClick={batDauTimBangGiongNoi} />
      </Tooltip>
      <Tooltip title="Tra cứu thuốc bằng ảnh">
        <Link to="/tra-cuu-anh" className="nut-tra-cuu-anh" aria-label="Tra cứu thuốc bằng ảnh">
          <CameraOutlined />
        </Link>
      </Tooltip>
    </div>
    </div>
  )
}
