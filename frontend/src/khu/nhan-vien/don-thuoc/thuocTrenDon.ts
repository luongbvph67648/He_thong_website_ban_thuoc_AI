/** Màu nhãn độ tin cậy AI06: dưới 50% đỏ (dược sĩ phải kiểm tra kỹ), dưới 80% cam, còn lại xanh. */
export function mauDoTinCay(v: number): 'red' | 'orange' | 'green' {
  if (v < 0.5) return 'red'
  if (v < 0.8) return 'orange'
  return 'green'
}
