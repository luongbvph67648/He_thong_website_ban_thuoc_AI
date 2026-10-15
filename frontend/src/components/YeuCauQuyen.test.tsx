import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { usePhien } from '../stores/phien'
import { YeuCauQuyen } from './YeuCauQuyen'

function dangNhap(quyen: Record<string, 'day_du' | 'chi_xem'>, loai: 'khach' | 'noi_bo' = 'noi_bo') {
  usePhien.getState().dangNhap({ accessToken: 't', loai, hoSo: { id: 1, hoTen: 'A' }, quyen })
}

function dung(children: React.ReactNode) {
  return render(
    <MemoryRouter initialEntries={['/can-quyen?x=1']}>
      <Routes>
        <Route path="/can-quyen" element={children} />
        <Route path="/nhan-vien/dang-nhap" element={<p>TRANG DANG NHAP</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('YeuCauQuyen (route)', () => {
  beforeEach(() => usePhien.getState().dangXuat())

  it('chưa đăng nhập: chuyển tới đăng nhập nội bộ', () => {
    dung(<YeuCauQuyen ma="order.view">NOI DUNG</YeuCauQuyen>)
    expect(screen.getByText('TRANG DANG NHAP')).toBeInTheDocument()
    expect(screen.queryByText('NOI DUNG')).not.toBeInTheDocument()
  })

  it('đăng nhập bằng phiên khách: vẫn bị coi là chưa đăng nhập nội bộ', () => {
    dangNhap({ 'order.view': 'day_du' }, 'khach')
    dung(<YeuCauQuyen ma="order.view">NOI DUNG</YeuCauQuyen>)
    expect(screen.getByText('TRANG DANG NHAP')).toBeInTheDocument()
  })

  it('đăng nhập nhưng thiếu quyền: hiện 403, không lộ nội dung', () => {
    dangNhap({ 'stock.view': 'day_du' })
    dung(<YeuCauQuyen ma="order.view">NOI DUNG</YeuCauQuyen>)
    expect(screen.getByText('Bạn không có quyền truy cập trang này')).toBeInTheDocument()
    expect(screen.queryByText('NOI DUNG')).not.toBeInTheDocument()
  })

  it('có quyền: hiện nội dung', () => {
    dangNhap({ 'order.view': 'day_du' })
    dung(<YeuCauQuyen ma="order.view">NOI DUNG</YeuCauQuyen>)
    expect(screen.getByText('NOI DUNG')).toBeInTheDocument()
  })

  it('mức xem chấp nhận quyền chỉ xem; mức đầy đủ thì không', () => {
    dangNhap({ 'order.view': 'chi_xem' })
    dung(
      <>
        <YeuCauQuyen ma="order.view" muc="xem">
          XEM
        </YeuCauQuyen>
        <YeuCauQuyen ma="order.view" muc="day_du">
          SUA
        </YeuCauQuyen>
      </>,
    )
    expect(screen.getByText('XEM')).toBeInTheDocument()
    expect(screen.queryByText('SUA')).not.toBeInTheDocument()
  })

  it('nhiều mã quyền: có một trong số đó là qua', () => {
    dangNhap({ 'order.pick': 'day_du' })
    dung(<YeuCauQuyen ma={['order.pick', 'shipment.create']}>NOI DUNG</YeuCauQuyen>)
    expect(screen.getByText('NOI DUNG')).toBeInTheDocument()
  })
})

describe('YeuCauQuyen (nút)', () => {
  beforeEach(() => usePhien.getState().dangXuat())

  it('thiếu quyền hoặc chưa đăng nhập: ẩn hẳn, không hiện 403 hay chuyển hướng', () => {
    dung(
      <YeuCauQuyen ma="order.confirm" kieu="nut">
        <button>Xác nhận</button>
      </YeuCauQuyen>,
    )
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByText('TRANG DANG NHAP')).not.toBeInTheDocument()
  })

  it('quyền chỉ xem: nút thao tác bị ẩn', () => {
    dangNhap({ 'order.confirm': 'chi_xem' })
    dung(
      <YeuCauQuyen ma="order.confirm" kieu="nut">
        <button>Xác nhận</button>
      </YeuCauQuyen>,
    )
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('quyền đầy đủ: hiện nút', () => {
    dangNhap({ 'order.confirm': 'day_du' })
    dung(
      <YeuCauQuyen ma="order.confirm" kieu="nut">
        <button>Xác nhận</button>
      </YeuCauQuyen>,
    )
    expect(screen.getByRole('button', { name: 'Xác nhận' })).toBeInTheDocument()
  })
})
