# Frontend: quy ước React

Đọc kèm `docs/spec/09-frontend.md` (trang, route, quy tắc hiển thị) và `06-api.md` (API).

## Cấu trúc
```
src/
  main.tsx, App.tsx          # router gốc, QueryClientProvider, ConfigProvider (vi_VN)
  api/schema.d.ts            # SINH TỰ ĐỘNG bằng `npm run gen:api`, không sửa tay
  api/client.ts              # openapi-fetch: gắn access token, refresh 1 lần khi 401
  khu/cua-hang/              # layout + trang của khách (/)
  khu/nhan-vien/             # layout + trang dược sĩ, kho (/nhan-vien)
  khu/quan-tri/              # layout + trang Admin (/quan-tri)
  components/                # thành phần dùng chung (BangLoc, GiaTien, NhanTrangThai, TaiAnh...)
  lib/                       # dinhDang.ts, quyen.ts, gioHangLocal.ts
  stores/                    # Zustand: phien (token, hồ sơ, quyền), gioHang
```

## Quy tắc
- **Gọi API**
  - Chỉ gọi qua `api/client.ts` với type từ `schema.d.ts`; không tự viết type trùng với API.
  - Backend đổi schema thì chạy `npm run gen:api`.
- **Dữ liệu server**
  - Dùng TanStack Query (`useQuery`, `useMutation`) và invalidate theo query key sau mỗi mutation.
  - Zustand chỉ giữ phiên đăng nhập và giỏ hàng local.
- **Phân quyền trên UI**
  - Route khu `/nhan-vien` và `/quan-tri` bọc `<YeuCauQuyen ma="order.view">`; menu chỉ hiện mục người dùng có quyền.
  - Nút thao tác ẩn khi chỉ có quyền `chi_xem`.
  - UI chỉ là lớp phụ: backend vẫn kiểm tra quyền.
- **Hiển thị**
  - Tiền: `dinhDangTien()` (ví dụ `125.000 ₫`).
  - Ngày giờ: `dinhDangNgay()` theo Asia/Ho_Chi_Minh.
  - Trạng thái: `<NhanTrangThai loai="don_hang" giaTri=...>`, dùng bảng nhãn/màu trong `lib/trangThai.ts`, khớp enum trong ERD.
- **Thuốc kê đơn**
  - Không có nút "Thêm vào giỏ".
  - Thay bằng nút "Cần tư vấn từ dược sĩ", dẫn tới gửi đơn thuốc hoặc chat.
- **Form**
  - Dùng Ant Design `Form` và kiểm tra phía client giống ràng buộc backend.
  - Lỗi từ API: hiện `thong_diep`; gắn `chi_tiet` vào field tương ứng nếu có.
- **Ngôn ngữ:** toàn bộ chữ trên UI viết tiếng Việt có dấu. Tên file và component dùng PascalCase không dấu (`DanhSachDonHang.tsx`).
- **Responsive:** trang khách phải dùng được ở màn hình 360px; khu nội bộ tối thiểu 1280px.

## Test
- Vitest + Testing Library cho component có logic (giỏ hàng, tính tiền hiển thị, guard quyền).
- Playwright cho luồng chính (spec 10 mục 8), chạy với backend + seed mẫu.
