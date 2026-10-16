# Frontend: quy ước React

Đọc kèm `docs/spec/09-frontend.md` (trang, route, quy tắc hiển thị) và `06-api.md` (API).

## Cấu trúc
```
src/
  main.tsx, App.tsx          # router gốc, QueryClientProvider, ConfigProvider (vi_VN)
  api/schema.d.ts            # SINH TỰ ĐỘNG bằng `npm run gen:api`, không sửa tay
  api/client.ts              # openapi-fetch: gắn access token, refresh 1 lần khi 401, credentials: 'include'
  api/goi.ts                 # goi(): quy mọi kết quả (kể cả lỗi mạng, 204 không thân) về {ok, data|loi}; thongDiep* cho lỗi thường gặp
  api/khoiPhuc.ts            # khoiPhucPhien(): lấy lại phiên khi tải trang (chạy đúng một lần)
  api/dangXuat.ts            # dangXuatKhach(): thu hồi phiên phía máy chủ rồi xóa store
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
  - Backend đổi schema thì chạy `npm run gen:api` (backend phải đang chạy ở :8000) và commit `schema.d.ts`. Route backend mới nhớ khai `response_model` để type có dữ liệu thay vì `{}`.
  - Client tự gắn `Authorization` và làm mới token khi 401 (`api/xacThuc.ts`, QĐ-08); đừng tự `fetch` ngoài client.
- **Phiên đăng nhập** (`stores/phien.ts`): chỉ ở bộ nhớ, không persist, không đặt token hay hồ sơ vào localStorage/sessionStorage.
  - Phiên nội bộ giữ thêm `phaiDoiMatKhau` (và quyền, vai trò trong `hoSo`). `YeuCauQuyen`, `NhanVienLayout`, `QuanTriLayout` chuyển mọi trang nội bộ về `/nhan-vien/tai-khoan` khi cờ này bật; trang mới thuộc khu nội bộ nằm dưới các layout này thì được bảo vệ sẵn.
  - Đăng nhập/khôi phục phiên nội bộ dùng `phienTuNhanVien(NhanVienToi)` (`lib/hoSoNoiBo.ts`) để đổi hồ sơ API sang dạng lưu trong store; đăng xuất qua `dangXuatNoiBo()` / `dangXuatKhach()`.
  - Ngoại lệ duy nhất: khóa `phien_goi_y` (`khach` hoặc `noi_bo`, `lib/goiYPhien.ts`) để biết có nên thử lấy lại phiên khi tải trang. Store tự ghi/xóa khóa này trong `dangNhap`/`dangXuat`.
  - `daKhoiPhuc` là `false` khi đang lấy lại phiên lúc tải trang. Trang hay thành phần phân biệt "đã đăng nhập" với "chưa" (header, trang bắt đăng nhập) phải chờ cờ này, nếu không sẽ nhấp nháy hoặc chuyển hướng nhầm.
  - Làm mới token phải đi qua `lamMoiPhien` (có Web Locks): refresh token xoay vòng, hai lần làm mới cùng lúc bằng một cookie sẽ bị đăng xuất khắp nơi (QĐ-11). Không tự gọi `/auth/lam-moi` ở chỗ khác.
  - `?tiep=` sau đăng nhập đi qua `duongTiepTheo` (chỉ đường dẫn nội bộ).
- **Dữ liệu server**
  - Dùng TanStack Query (`useQuery`, `useMutation`) và invalidate theo query key sau mỗi mutation.
  - Zustand chỉ giữ phiên đăng nhập và giỏ hàng local.
- **Phân quyền trên UI**
  - Trang của khu nội bộ khai báo một lần trong `khu/nhan-vien/menu.ts` hoặc `khu/quan-tri/menu.ts` (đường dẫn, nhãn, mã quyền, mã chức năng); `router.tsx` sinh route bọc `<YeuCauQuyen ma=... muc="xem">` và menu lọc theo quyền từ cùng bảng đó. Thêm trang mới: thêm một dòng vào bảng, rồi thay `TrangDangXayDung` bằng trang thật. Test `router.test.tsx` đối chiếu bảng với spec 09 và `quyen.yaml`.
  - Nút thao tác bọc `<YeuCauQuyen ma="order.confirm" kieu="nut">` (mức đầy đủ), ẩn hẳn khi chỉ có `chi_xem`.
  - UI chỉ là lớp phụ: backend vẫn kiểm tra quyền.
- **Đồng bộ phiên nội bộ:** `KhungNoiBo` gọi `useDongBoPhienNoiBo` (`GET /noi-bo/toi` khi focus lại cửa sổ và mỗi 5 phút, cập nhật vai trò/quyền vào store) để Admin đổi phân quyền thì menu của nhân viên đang mở đổi theo. Test sự kiện focus phải phát `visibilitychange` trên `window` (TanStack Query nghe ở `window`, sự kiện phát từ `document` mà không nổi bọt sẽ không tới).
- **Liên kết trong trang con của khu quản trị/nhân viên** phải giữ tiền tố khu (`/quan-tri`, `/nhan-vien`): dựng từ `useLocation().pathname` hoặc dùng `<Link to=".." relative="path">`, không viết cứng `/khach-hang/1` (sẽ bật ra khu cửa hàng). Test trang con có ca chạy dưới tiền tố (`dung(duong, quyen, '/quan-tri')`).
- **Trạng thái đơn, thanh toán, kênh bán:** dùng `<NhanTrangThai loai=... giaTri=...>` (`lib/trangThai.ts`); thêm giá trị enum ở backend thì test `trangThai.test.ts` (đối chiếu `schema.d.ts`) báo thiếu nhãn.
- **Ô số có khoảng giá trị** (AD08...): không đặt `min`/`max` cho `InputNumber` của antd (nó âm thầm ép giá trị về khoảng); kiểm tra bằng hàm riêng (`lib/cauHinh.ts`), báo lỗi và tắt nút Lưu. Lưu cấu hình/phân quyền gửi kèm `phien_ban`; gặp 409 thì tải lại bản mới nhưng giữ giá trị người dùng đang gõ.
- **Giờ đến giây** (nhật ký): `dinhDangNgay(x, 'ngayGioGiay')`.
- **Cây kéo thả** (AD03, `khu/quan-tri/danh-muc/`): phép tính (vị trí đích, cấp tối đa, chống vòng) nằm ở `cayDanhMuc.ts` thuần để test từng ca; trang chỉ nối antd `Tree` với chúng. Vị trí thả của antd: `huong = info.dropPosition - Number(info.node.pos.split('-').pop())` (`-1` trước, `0` trong, `1` sau; `!dropToGap` là trong); `allowDrop` nhận hướng tương đối. jsdom không có hình học nên kéo thả thật chỉ kiểm bằng Chromium.
- **Ô nhập của Admin** (`lib/duLieuChung.ts`): `loiTen`, `loiDuongDan`, `loiVanBan` cùng quy tắc và bảng ca với backend (`core/kieu_du_lieu.py`); form gắn lỗi máy chủ vào ô qua `loiTheoTruong`. Bảng dùng chung nhiều nhóm (AD05) gọi API qua `goiApi.ts` (một `switch` theo nhóm, giữ kiểu từ `schema.d.ts`), không ghép chuỗi đường dẫn.
- **Mật khẩu tạm** (AD01) chỉ nằm trong state của một Modal mount có điều kiện: đóng là biến khỏi DOM, không lưu ở store/cache/URL.
- **Thông báo nội bộ:** `components/ChuongThongBao.tsx` (query key `['noi-bo', 'thong-bao', ...]`, làm mới mỗi phút). Chỉ điều hướng tới `lien_ket` khi là đường dẫn nội bộ. Không dùng antd `List` (deprecated từ 6.6): dùng phần tử tự dựng hoặc `<button>`.
- **Hiển thị**
  - Tiền: `dinhDangTien()` (ví dụ `125.000 ₫`).
  - Ngày giờ: `dinhDangNgay()` theo Asia/Ho_Chi_Minh.
  - Trạng thái: `<NhanTrangThai loai="don_hang" giaTri=...>`, dùng bảng nhãn/màu trong `lib/trangThai.ts`, khớp enum trong ERD.
- **Thuốc kê đơn**
  - Không có nút "Thêm vào giỏ".
  - Thay bằng nút "Cần tư vấn từ dược sĩ", dẫn tới gửi đơn thuốc hoặc chat.
- **Form**
  - Dùng Ant Design `Form` và kiểm tra phía client giống ràng buộc backend (`lib/dienThoai.ts`, `lib/matKhau.ts` có test cùng bảng ca với backend).
  - Nhiều `Form` cùng vị trí trong JSX (ví dụ các bước của form nhiều bước) PHẢI có `key` khác nhau: không có key thì React dùng lại một phiên bản và nó giữ instance `form` cũ, `setFields`/`getFieldValue` của form mới sẽ không có tác dụng.
  - Lỗi từ API: hiện `thong_diep`; gắn `chi_tiet` vào field tương ứng nếu có.
- **Ngôn ngữ:** toàn bộ chữ trên UI viết tiếng Việt có dấu. Tên file và component dùng PascalCase không dấu (`DanhSachDonHang.tsx`).
- **Responsive:** trang khách phải dùng được ở màn hình 360px; khu nội bộ tối thiểu 1280px.

## Test
- `npm test` chạy vitest ở chế độ theo dõi; một lần: `npm test -- --run`. Test ở cạnh file (`x.test.ts(x)`).
- `src/test/render.tsx::renderTai(duong, phien?)` dựng ứng dụng thật (router + provider) tại một đường dẫn với phiên giả; dùng cho test điều hướng và phân quyền.
- Test hàm thời gian phải đúng ở mọi múi giờ máy (`TZ=America/Los_Angeles npm test -- --run` cũng phải xanh).
- Vitest + Testing Library cho component có logic (giỏ hàng, tính tiền hiển thị, guard quyền).
- Playwright cho luồng chính (spec 10 mục 8), chạy với backend + seed mẫu.
