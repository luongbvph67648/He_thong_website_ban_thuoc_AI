import type { ReactNode } from 'react'
import Markdown from 'react-markdown'
import { Link } from 'react-router-dom'
import { laLienKetNgoai, urlMarkdownAnToan } from '../lib/lienKet'

/**
 * Hiển thị nội dung Markdown của Admin (bài viết, chính sách, FAQ). `react-markdown` không render HTML thô (`<script>`,
 * `<img onerror>` hiện thành chữ), nên an toàn với nội dung do người khác soạn; liên kết và ảnh còn đi qua
 * `urlMarkdownAnToan`. Liên kết nội bộ dùng `Link` (không tải lại trang), liên kết ngoài mở tab mới với `noopener`.
 */
export function NoiDungMarkdown({ noiDung }: { noiDung: string }): ReactNode {
  return (
    <div className="noi-dung-markdown" style={{ overflowWrap: 'anywhere', lineHeight: 1.7 }}>
      <Markdown
        urlTransform={urlMarkdownAnToan}
        components={{
          a: ({ href, children }) => {
            if (!href) return <>{children}</>
            if (href.startsWith('/')) return <Link to={href}>{children}</Link>
            return (
              <a href={href} {...(laLienKetNgoai(href) ? { target: '_blank', rel: 'noopener noreferrer' } : {})}>
                {children}
              </a>
            )
          },
          img: ({ src, alt }) => (src ? <img src={src} alt={alt ?? ''} loading="lazy" style={{ maxWidth: '100%' }} /> : null),
        }}
      >
        {noiDung}
      </Markdown>
    </div>
  )
}
