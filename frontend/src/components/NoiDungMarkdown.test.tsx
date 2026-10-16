import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { urlMarkdownAnToan } from '../lib/lienKet'
import { NoiDungMarkdown } from './NoiDungMarkdown'

const dung = (noiDung: string) =>
  render(
    <MemoryRouter>
      <NoiDungMarkdown noiDung={noiDung} />
    </MemoryRouter>,
  )

describe('urlMarkdownAnToan', () => {
  it.each(['/danh-muc/thuoc', 'https://example.com/a', 'http://example.com', 'mailto:a@b.vn'])('%s hợp lệ', (u) =>
    expect(urlMarkdownAnToan(u)).toBe(u),
  )
  it.each(['javascript:alert(1)', 'JAVASCRIPT:alert(1)', 'data:text/html,x', '//evil.example', 'vbscript:x', ' javascript:x', 'mailto:'])(
    '%j bị bỏ',
    (u) => expect(urlMarkdownAnToan(u)).toBe(''),
  )
})

describe('NoiDungMarkdown', () => {
  it('render tiêu đề, danh sách, đậm', () => {
    dung('## Rửa tay\n\n- một\n- hai\n\n**đậm**')
    expect(screen.getByRole('heading', { name: 'Rửa tay', level: 2 })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByText('đậm').tagName).toBe('STRONG')
  })

  it('HTML thô hiện thành chữ, không thành phần tử (không có script, onerror)', () => {
    const { container } = dung('<script>window.hack=1</script>\n\n<img src=x onerror="window.hack=2">\n\n<b>b</b>')
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('b')).toBeNull()
    expect((window as unknown as { hack?: number }).hack).toBeUndefined()
  })

  it('liên kết javascript: mất href; liên kết an toàn giữ; ngoài thì mở tab mới và noopener', () => {
    const { container } = dung('[xấu](javascript:alert(1)) [nội bộ](/danh-muc/thuoc) [ngoài](https://example.com/x) [giao thức tương đối](//evil.example)')
    expect(screen.queryByRole('link', { name: 'xấu' })).toBeNull() // không còn là liên kết
    expect(container).toHaveTextContent('xấu') // chữ vẫn hiện, chỉ mất liên kết
    expect(screen.getByRole('link', { name: 'nội bộ' })).toHaveAttribute('href', '/danh-muc/thuoc')
    const ngoai = screen.getByRole('link', { name: 'ngoài' })
    expect(ngoai).toHaveAttribute('target', '_blank')
    expect(ngoai).toHaveAttribute('rel', 'noopener noreferrer')
    expect(screen.queryByRole('link', { name: 'giao thức tương đối' })).toBeNull()
  })

  it('ảnh: nhận /... và https, bỏ javascript: và data:', () => {
    const { container } = dung('![a](/api/v1/tep/bai-viet/a.jpg) ![b](https://x.vn/b.png) ![c](javascript:alert(1)) ![d](data:image/svg+xml,x)')
    const nguon = [...container.querySelectorAll('img')].map((i) => i.getAttribute('src'))
    expect(nguon).toEqual(['/api/v1/tep/bai-viet/a.jpg', 'https://x.vn/b.png'])
  })
})
