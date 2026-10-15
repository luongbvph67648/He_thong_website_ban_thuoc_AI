import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { khoiPhucPhien } from './api/khoiPhuc'

// Lấy lại phiên đăng nhập (nếu có) song song với việc dựng giao diện; chạy đúng một lần mỗi lần tải trang.
void khoiPhucPhien()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
