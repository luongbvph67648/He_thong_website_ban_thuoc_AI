# 06. API

## 1. Nguyên tắc
- REST JSON, tiền tố `/api/v1`. Tên đường dẫn là tiếng Việt không dấu, nối bằng gạch ngang (`/don-hang`, `/phieu-nhap`).
- Tên trường JSON giữ đúng tên cột ERD (snake_case không dấu). Tiền trả về dạng **chuỗi số** (`"125000.00"`) để không mất chính xác. Frontend định dạng lại khi hiển thị.
- Thời gian trả về ISO 8601 có múi giờ UTC (`2026-10-15T03:00:00Z`). Ngày (HSD) trả về `YYYY-MM-DD`.
- Với khách, tài nguyên được định danh bằng mã (`ma_don`, `ma_yeu_cau`) thay vì `id`. Nội bộ được dùng `id`.
- OpenAPI tự sinh tại `/docs` và `/openapi.json`. Mỗi route có `summary` tiếng Việt kèm mã chức năng, ví dụ `"Xác nhận đơn hàng (DS02)"`.

## 2. Nhóm route
| Tiền tố | Ai gọi | Xác thực |
|---|---|---|
| `/api/v1/auth/*` | Khách | Đăng ký, đăng nhập, làm mới, đăng xuất, OTP, quên mật khẩu |
| `/api/v1/noi-bo/auth/*` | Nhân viên | Đăng nhập, làm mới, đăng xuất, đổi mật khẩu |
| `/api/v1/san-pham`, `/danh-muc`, `/tim-kiem`, `/bai-viet`, `/banner`, `/hoat-chat` | Công khai | `khach_tuy_chon` |
| `/api/v1/don-thuoc` (POST), `/api/v1/xac-nhan-don/{token}` | Khách vãng lai | OTP hoặc mã truy cập trong link |
| `/api/v1/tu-van/*` (chat SSE, WebSocket), `/api/v1/tra-cuu-anh` | Khách (cả vãng lai) | `khach_tuy_chon` + giới hạn tần suất |
| `/api/v1/toi/*` | Khách thành viên | `khach_hien_tai`; mọi dữ liệu lọc theo khách trong token |
| `/api/v1/noi-bo/*` | Nhân viên | `yeu_cau_quyen(...)` |
| `/api/v1/webhook/*` | VNPay, MoMo, GHN | Chữ ký hoặc token của đối tác (spec 08) |
| `/api/v1/health` | Hạ tầng | Không. Trả 200 `{"trang_thai": "ok", "db": "ok"}`; CSDL không truy vấn được thì 503 `{"trang_thai": "loi", "db": "loi"}` (không lộ chi tiết lỗi) |

**Ví dụ đường dẫn chuẩn:**
- Khách:
  - `GET /api/v1/toi/don-hang`
  - `GET /api/v1/toi/don-hang/{ma_don}`
  - `POST /api/v1/toi/don-hang/{ma_don}/huy`
- Nội bộ:
  - `GET /api/v1/noi-bo/don-hang?trang_thai=cho_xac_nhan`
  - `POST /api/v1/noi-bo/don-hang/{id}/xac-nhan`
  - `POST /api/v1/noi-bo/phieu-huy/{id}/duyet`
- Hành động nghiệp vụ dùng `POST /<tài nguyên>/{id}/<động từ>` (`/xac-nhan`, `/huy`, `/duyet`, `/tu-choi`, `/nhan-xu-ly`), không dùng `PATCH trang_thai`.

## 3. Xác thực
- **Access token:** JWT HS256.
  - Claim: `sub` (id), `aud` (`khach` | `noi_bo`), `exp` (15 phút), `jti`.
  - Gửi qua header `Authorization: Bearer <token>`.
  - Đăng nhập và làm mới (`POST .../auth/dang-nhap`, `POST .../auth/lam-moi`) trả thân JSON `{"access_token": "<jwt>"}` (kèm cookie refresh token). Frontend (`api/xacThuc.ts`) dựa vào đúng khóa `access_token`.
  - Làm mới: khách `POST /api/v1/auth/lam-moi`, nhân viên `POST /api/v1/noi-bo/auth/lam-moi`; cookie refresh được gửi theo `Path` của từng loại.
  - Không lưu quyền trong token. Quyền đọc từ DB (spec 03 mục 8).
- **Refresh token:**
  - Chuỗi ngẫu nhiên 256 bit, đặt trong cookie `HttpOnly; Secure; SameSite=Lax`, `Path=/api/v1/auth` (khách) hoặc `/api/v1/noi-bo/auth` (nhân viên).
  - Lưu SHA-256 vào `phien_dang_nhap`.
  - Xoay vòng mỗi lần làm mới. Dùng lại một token đã thu hồi thì thu hồi toàn bộ phiên của tài khoản đó (phát hiện bị đánh cắp).
- **Mật khẩu:** Argon2id. Tối thiểu 8 ký tự, có chữ và số.
- **OTP:** 6 chữ số, lưu hash, hết hạn 5 phút, tối đa 5 lần thử.
  - `muc_dich`: `dang_ky`, `quen_mat_khau`, `don_thuoc_khach`.
  - Phản hồi giống nhau dù SĐT có tồn tại hay không, để chống dò tài khoản.

### 3.1 Đăng ký khách (KVL09)
- `POST /api/v1/auth/otp` `{so_dien_thoai, muc_dich: "dang_ky"}` -> 200 `{da_gui: true, het_han_giay: 300}`. Phản hồi giống hệt dù số đã đăng ký hay chưa (số đã đăng ký nhận SMS "đã có tài khoản"). `429 QUA_GIOI_HAN` kèm `Retry-After` theo `cau_hinh.gioi_han_otp` (theo SĐT và theo IP). `502 LOI_DOI_TAC` khi không gửi được tin nhắn.
- `POST /api/v1/auth/dang-ky` `{so_dien_thoai, otp, mat_khau, ho_ten, email?, dong_y_chinh_sach: true}` -> 201 `{id, ho_ten, so_dien_thoai, email}`. `422 OTP_SAI` (kèm `chi_tiet.so_lan_con_lai`; hết lượt thử cũng là `OTP_SAI`), `422 OTP_HET_HAN`, `409 TRUNG_DU_LIEU` (`chi_tiet.truong`).
- SĐT nhận dạng `+84 912 345 678`, `0912.345.678`... và lưu dạng `0xxxxxxxxx`; chỉ số di động Việt Nam.
- Route cần giữ thay đổi dù trả lỗi (đếm lần thử OTP, đếm đăng nhập sai) phải TRẢ VỀ lỗi bằng `core.loi.tra_loi(...)`, không `raise` (raise làm rollback).

### 3.2 Đăng nhập, phiên và lấy lại mật khẩu của khách (KVL10)
- `POST /api/v1/auth/dang-nhap` `{ten_dang_nhap, mat_khau}` -> 200 `{access_token, token_type: "bearer", het_han_giay, khach_hang: {id, ho_ten, so_dien_thoai, email}}` và cookie refresh token. `ten_dang_nhap` là số điện thoại (mọi dạng được chuẩn hóa như ở 3.1) hoặc email (không phân biệt hoa thường).
  - `401 SAI_THONG_TIN_DANG_NHAP` cho mọi trường hợp sai: sai mật khẩu, tài khoản không tồn tại hoặc đã xóa, định danh không phải số/email. Cùng thân phản hồi và cùng chi phí tính toán (luôn băm một lần), để không dò được tài khoản.
  - `403 TAI_KHOAN_BI_KHOA` (kèm `chi_tiet.thu_lai_sau_giay`) khi đang bị khóa tạm: sai `cau_hinh.so_lan_dang_nhap_sai_toi_da` lần liên tiếp thì khóa `cau_hinh.thoi_gian_khoa_dang_nhap_phut` phút (mặc định 5 lần, 15 phút). Đang khóa thì mật khẩu đúng cũng bị từ chối và không kéo dài thời gian khóa. Đăng nhập đúng xóa bộ đếm. Tài khoản Admin khóa (`trang_thai = bi_khoa`) chỉ trả `403 TAI_KHOAN_BI_KHOA` (không kèm thời gian) khi nhập ĐÚNG mật khẩu; sai mật khẩu vẫn là 401 như trên.
  - `429 QUA_GIOI_HAN` (kèm `Retry-After`) khi một IP thử quá 20 lần trong 10 phút, tính cả lần đúng.
- `POST /api/v1/auth/lam-moi` (cookie refresh, không thân) -> 200 `{access_token, token_type, het_han_giay}` và cookie refresh mới; token cũ bị thu hồi. Dùng lại token đã thu hồi thì thu hồi toàn bộ phiên của tài khoản. Các lỗi `401 CHUA_DANG_NHAP` (không có cookie/token lạ/đã thu hồi hoặc của loại tài khoản khác), `401 TOKEN_HET_HAN` (quá `REFRESH_NGAY`) và `403 TAI_KHOAN_BI_KHOA` do Admin khóa hoặc xóa mềm đều kèm lệnh xóa cookie; riêng Admin khóa/xóa mềm giữa chừng thì mọi phiên bị thu hồi. **Khóa tạm do đoán sai mật khẩu** thì trả `403 TAI_KHOAN_BI_KHOA` kèm `chi_tiet.thu_lai_sau_giay`, KHÔNG xoay vòng, KHÔNG thu hồi phiên nào, KHÔNG xóa cookie (người lạ gửi sai mật khẩu không được đăng xuất chủ tài khoản); hết khóa thì chính refresh token đó dùng tiếp được. Lúc làm mới, dòng tài khoản được khóa (`FOR UPDATE`) trước dòng phiên, cùng thứ tự với đăng nhập, đổi mật khẩu và đặt lại mật khẩu (tránh deadlock và bảo đảm "thu hồi tất cả" thấy cả phiên vừa cấp).
- `POST /api/v1/auth/dang-xuat` -> 204: thu hồi đúng phiên của cookie hiện tại và xóa cookie. Gọi lại, không có cookie hay cookie lạ vẫn 204.
- `POST /api/v1/auth/otp` với `muc_dich: "quen_mat_khau"`, `kenh: "sms" | "email"` (mặc định `sms`; `email` chỉ hợp lệ với `quen_mat_khau`) -> 200 `{da_gui: true, het_han_giay: 300}`, giống hệt dù số có tài khoản hay không. Số chưa có tài khoản (hoặc đã xóa) nhận một SMS "chưa có tài khoản" thay cho mã. `kenh = email` mà tài khoản chưa có email thì mã gửi qua SMS. Giới hạn gửi tính riêng cho từng mục đích.
- `POST /api/v1/auth/dat-lai-mat-khau` `{so_dien_thoai, otp, mat_khau_moi}` -> 200 `{da_dat_lai: true}`. Lỗi `422 OTP_SAI` / `OTP_HET_HAN` như 3.1; mật khẩu yếu là `400` (kiểm tra trước OTP nên không tiêu mã). Thành công thì đổi mật khẩu, xóa bộ đếm sai và `khoa_den`, thu hồi MỌI phiên của khách đó. Không mở khóa tài khoản Admin đã khóa.
- **Cookie refresh token:** tên `refresh_token`, `HttpOnly; SameSite=Lax; Secure` (tắt `Secure` bằng `COOKIE_SECURE=false` khi dev qua http), `Path=/api/v1/auth`, `Max-Age = REFRESH_NGAY` ngày. Refresh token không bao giờ nằm trong thân JSON.
- `GET /api/v1/toi` -> 200 `{id, ho_ten, so_dien_thoai, email}` của khách trong token. Mọi route `/api/v1/toi/*` phải dùng `Depends(khach_hien_tai)` (có test duyệt OpenAPI: không token thì 401).
- **Guard (`core/phan_quyen.py`):** `khach_hien_tai` đòi access token `aud = khach`, rồi đọc tài khoản từ DB ở MỖI request (tài khoản phải tồn tại, `hoat_dong`, không `khoa_den`) nên khóa tài khoản có hiệu lực ngay chứ không đợi token hết hạn. Token hết hạn là `401 TOKEN_HET_HAN`; mọi token sai khác là `401 CHUA_DANG_NHAP`; tài khoản bị khóa là `403 TAI_KHOAN_BI_KHOA`. `khach_tuy_chon` cho route công khai: không token, token vô nghĩa, token nội bộ hoặc tài khoản bị khóa thì coi là khách vãng lai; chỉ token khách hết hạn mới trả `TOKEN_HET_HAN` để client làm mới.

### 3.3 Xác thực và hồ sơ nhân viên (NV01, NV02)
- **Cookie refresh token nhân viên:** tên `refresh_token_noi_bo`, `Path=/api/v1/noi-bo/auth`, các thuộc tính còn lại như khách (mục 3.2). Tên và `Path` khác với khách nên trình duyệt đăng nhập cả hai chỉ gửi đúng cookie cho đúng nhóm endpoint; refresh token của loại này đưa vào cửa của loại kia bị từ chối mà không thu hồi gì.
- `POST /api/v1/noi-bo/auth/dang-nhap` `{email, mat_khau}` -> 200 `{access_token, token_type, het_han_giay, nhan_vien: NhanVienToi}` (access token `aud = noi_bo`). Email không phân biệt hoa thường. Lỗi, khóa tạm (`so_lan_dang_nhap_sai_toi_da`, `thoi_gian_khoa_dang_nhap_phut`), giới hạn 20 lần/10 phút mỗi IP (bộ đếm riêng với cửa khách) và chống dò tài khoản y như `POST /auth/dang-nhap` của khách (mục 3.2). Tài khoản còn `phai_doi_mat_khau` vẫn đăng nhập được.
- `POST /api/v1/noi-bo/auth/lam-moi`, `POST /api/v1/noi-bo/auth/dang-xuat`: như của khách (kể cả cách xử lý khóa tạm và Admin khóa ở mục 3.2). Đây cùng với `dang-nhap` là ba route công khai duy nhất dưới `/noi-bo` (chưa có phiên thì không thể có quyền).
- `POST /api/v1/noi-bo/auth/doi-mat-khau` `{mat_khau_cu, mat_khau_moi}` (cần `profile.self`, dùng được cả khi đang bị bắt đổi mật khẩu) -> 200 như đăng nhập (phiên MỚI).
  - Thành công: thu hồi MỌI phiên cũ của nhân viên đó (kể cả thiết bị khác), bỏ cờ `phai_doi_mat_khau`, cấp phiên mới cho thiết bị đang đổi, ghi nhật ký `doi_mat_khau`.
  - `422 MAT_KHAU_CU_SAI` khi mật khẩu hiện tại sai; lần sai được đếm như đăng nhập sai, đủ số lần thì `403 TAI_KHOAN_BI_KHOA` (kèm `chi_tiet.thu_lai_sau_giay`), khóa tạm VÀ thu hồi mọi phiên (người đang gọi có thể cầm phiên bị đánh cắp). Đang khóa thì mật khẩu đúng cũng không đổi được.
  - `400` khi mật khẩu mới yếu hoặc trùng mật khẩu cũ (kiểm tra trước, không bị đếm là lần sai).
- `GET /api/v1/noi-bo/toi` -> 200 `NhanVienToi`: `{id, ma_nhan_vien, ho_ten, email, so_dien_thoai, vai_tro: {ma, ten}, phai_doi_mat_khau, quyen: {<mã quyền>: "day_du" | "chi_xem"}}`. Dùng được cả khi còn `phai_doi_mat_khau` (giao diện đọc cờ này để chuyển sang màn đổi mật khẩu). Không bao giờ có mật khẩu hay hash.
- `PATCH /api/v1/noi-bo/toi` `{ho_ten?, so_dien_thoai?}` -> `NhanVienToi`. Chỉ đổi trường được gửi; `so_dien_thoai` null hoặc rỗng là xóa số. Trường khác (email do Admin quản lý ở AD01, vai trò, trạng thái, cờ đổi mật khẩu) bị từ chối `400`. Ghi nhật ký `sua` với giá trị cũ/mới, số điện thoại chỉ ghi dạng che (`091***678`).
- **Thông báo của tôi** (`profile.self`; thông báo của người khác hoặc của khách là `404`):
  - `GET /api/v1/noi-bo/thong-bao?da_doc=&trang=&kich_thuoc=` -> trang `ThongBaoDoc` `{id, loai, tieu_de, noi_dung, lien_ket, da_doc, created_at}`, mới nhất trước.
  - `GET /api/v1/noi-bo/thong-bao/so-chua-doc` -> `{so_chua_doc}` (chuông thông báo, làm mới mỗi phút).
  - `POST /api/v1/noi-bo/thong-bao/{id}/da-doc` (gọi lại vẫn 200), `POST /api/v1/noi-bo/thong-bao/da-doc-tat-ca` -> `{da_cap_nhat}`.
  - `lien_ket` chỉ là đường dẫn nội bộ của ứng dụng (bắt đầu bằng một `/`); service tạo thông báo từ chối URL ngoài, và giao diện cũng không bao giờ điều hướng tới URL ngoài.

### 3.4 Quản lý tài khoản nhân viên (AD01, `staff.manage`)
Mọi route dưới `/api/v1/noi-bo/nhan-vien`; đọc cần mức `xem`, ghi cần `day_du` VÀ người thực hiện phải thuộc vai trò ADMIN (`dam_bao_la_admin`, `403 KHONG_CO_QUYEN`): `staff.manage` không gán được cho vai trò khác qua AD18 (mục 3.5), lớp này chặn thêm trường hợp dữ liệu cấu hình sai (gán thẳng vào DB) biến thành quyền tạo Admin. `{id}` là số nguyên 1..2147483647 (ngoài khoảng là `400 DU_LIEU_KHONG_HOP_LE`, không bao giờ 500; id hợp lệ nhưng không có là `404`). Phản hồi `NhanVienQuanTriDoc` `{id, ma_nhan_vien, ho_ten, email, so_dien_thoai, vai_tro: {ma, ten}, trang_thai, phai_doi_mat_khau, khoa_den, created_at, updated_at}` không bao giờ có mật khẩu hay hash; nhân viên đã xóa mềm không xuất hiện ở đâu (`404`).
- `GET /noi-bo/nhan-vien?q=&vai_tro=&trang_thai=&sap_xep=&trang=&kich_thuoc=` -> trang `NhanVienQuanTriDoc`. `sap_xep` (mục 5) nhận `created_at` (mặc định `-created_at`, mới tạo nhất trước), `ma_nhan_vien`, `ho_ten`, `email` (tên và email không phân biệt dấu/hoa thường); trường khác là `400`; luôn thêm `id` làm khóa phụ nên thứ tự ổn định giữa các trang. `q` tìm tên không phân biệt dấu/hoa thường, email, mã (ký tự `%` `_` `\` trong `q` được hiểu theo nghĩa đen). `GET /noi-bo/nhan-vien/{id}` -> `NhanVienQuanTriDoc`.
- `POST /noi-bo/nhan-vien` `{ho_ten, email, so_dien_thoai?, vai_tro}` -> 201 `NhanVienCoMatKhauTam` (= `NhanVienQuanTriDoc` + `mat_khau_tam`). Mật khẩu tạm 12 ký tự ngẫu nhiên (CSPRNG, chữ và số, bỏ ký tự dễ nhầm), **chỉ có trong phản hồi này**, DB chỉ lưu hash; tài khoản có `phai_doi_mat_khau = true`. Email lưu chữ thường, không trùng với bất kỳ nhân viên nào kể cả đã xóa mềm (`409 TRUNG_DU_LIEU`, `chi_tiet.truong = "email"`); `vai_tro` không tồn tại là `400 DU_LIEU_KHONG_HOP_LE`.
- `PATCH /noi-bo/nhan-vien/{id}` `{ho_ten?, email?, so_dien_thoai?, vai_tro?}` -> `NhanVienQuanTriDoc`. Chỉ đổi trường được gửi (`so_dien_thoai` rỗng/null là xóa số; trường lạ là `400`). **Đổi vai trò thu hồi mọi phiên của nhân viên đó** (phiên cũ mang quyền cũ).
- `POST /noi-bo/nhan-vien/{id}/khoa`, `/mo-khoa` -> `NhanVienQuanTriDoc`. Khóa: `trang_thai = bi_khoa` và thu hồi mọi phiên ngay, nên refresh token đang dùng bị coi là đã thu hồi (`401 CHUA_DANG_NHAP`, cookie bị xóa, mục 3.2) còn đăng nhập bằng mật khẩu đúng nhận `403 TAI_KHOAN_BI_KHOA`; mở khóa xóa luôn `khoa_den` và bộ đếm đăng nhập sai.
- `POST /noi-bo/nhan-vien/{id}/dat-lai-mat-khau` -> `NhanVienCoMatKhauTam`: sinh mật khẩu tạm mới, đặt `phai_doi_mat_khau`, thu hồi mọi phiên, xóa khóa tạm (`khoa_den`, bộ đếm sai). Không mở khóa của Admin (`trang_thai` giữ nguyên, dùng `mo-khoa`).
- `DELETE /noi-bo/nhan-vien/{id}` -> 204. Xóa mềm (`deleted_at`) và thu hồi mọi phiên; bản ghi và nhật ký cũ giữ nguyên, **không có xóa cứng**.
- **Quy tắc an toàn:** Admin không tự khóa, tự xóa, tự đổi vai trò, tự đặt lại mật khẩu của mình (`403 TU_THAY_DOI_KHONG_DUOC`; tự đổi mật khẩu dùng `doi-mat-khau` ở mục 3.3). Mọi thao tác làm Admin hoạt động cuối cùng mất khả năng đăng nhập (khóa, xóa, hạ vai trò) là `409 PHAI_CON_ADMIN`. Để hai Admin không thể đồng thời làm nhau mất quyền mà vượt kiểm tra, mỗi thao tác khóa dòng đích và MỌI dòng Admin chưa xóa trong một câu `ORDER BY id FOR UPDATE`.
- Mọi thao tác ghi nhật ký (`tao`, `sua`, `khoa`, `mo_khoa`, `dat_lai_mat_khau`, `xoa`) với giá trị cũ/mới; mật khẩu tạm và hash không bao giờ vào nhật ký, số điện thoại ghi dạng che.

### 3.5 Vai trò và phân quyền (AD18, `role.manage`)
Mọi route dưới `/api/v1/noi-bo/vai-tro`; `{ma}` chỉ gồm `A-Z` và `_`. Ghi cần `role.manage` ở mức `day_du` VÀ người thực hiện thuộc vai trò ADMIN (như mục 3.4: `role.manage` không gán được cho vai trò khác, nếu được thì người nhận tự cấp thêm quyền cho vai trò của mình).
- `GET /noi-bo/vai-tro` -> `[{ma, ten, mo_ta, so_nhan_vien, so_quyen, chinh_sua_duoc}]`.
- `GET /noi-bo/vai-tro/{ma}` -> `{ma, ten, mo_ta, so_nhan_vien, chinh_sua_duoc, phien_ban, quyen: [...]}`: **toàn bộ** mã quyền của hệ thống (dạng `{ma, nhom, mo_ta, muc: "day_du" | "chi_xem" | null, bat_buoc, chi_cho_vai_tro}`) để giao diện dựng ma trận một lần gọi. `phien_ban` là dấu vân tay 16 ký tự hex của tập (mã quyền, mức) hiện có: chỉ phụ thuộc nội dung quyền, nên lưu lại bản cũ thì phiên bản cũ trở lại. `chi_cho_vai_tro` là vai trò duy nhất được giữ quyền đó, hoặc `null`.
- `PUT /noi-bo/vai-tro/{ma}/quyen` `{quyen: {<mã quyền>: "day_du" | "chi_xem"}, phien_ban}` -> `VaiTroChiTiet`. Thay TOÀN BỘ quyền của vai trò: mã không có trong `quyen` là bị gỡ. Khóa dòng vai trò `FOR UPDATE` nên hai Admin sửa cùng lúc được tuần tự hóa.
  - `ADMIN` không sửa được (`409 PHAI_CON_ADMIN`; `chinh_sua_duoc = false`). Kiểm tra này đứng trước mọi kiểm tra khác.
  - `400 DU_LIEU_KHONG_HOP_LE` (kèm danh sách lỗi trong `chi_tiet`, trả hết một lần) khi: thiếu hoặc sai định dạng `phien_ban`; mã quyền không có trong `quyen.yaml`; `profile.self` bị gỡ hoặc hạ xuống `chi_xem` (mọi nhân viên phải tự đổi được mật khẩu và hồ sơ); `content.professional.edit` / `content.approve` gán cho vai trò khác `PHARMACIST` (quyền chuyên môn, spec 03 mục 7); hoặc gán cho vai trò khác ADMIN một trong 18 quyền mà ma trận spec 03 chỉ cấp cho ADMIN (quản trị tài khoản và phân quyền, duyệt phiếu kho, xác nhận hoàn tiền, cấu hình, AI, nhật ký, báo cáo toàn hệ thống...). Lý do: `staff.manage`/`role.manage` cho phép tự tạo Admin hay tự cấp quyền (leo thang đặc quyền); `refund.confirm`, `stock_doc.approve` làm một người vừa lập, vừa duyệt (spec 03 mục 7). Vai trò đã giữ sẵn quyền loại này do cấu hình sai thì gỡ được bằng cách gửi bản không có nó.
  - `409 DU_LIEU_DA_THAY_DOI` khi `phien_ban` không còn là bản hiện tại (Admin khác vừa đổi quyền của vai trò này). Không ghi gì; client tải lại bản mới rồi quyết định, để một trang mở từ trước không ngầm cấp lại quyền vừa bị gỡ. Kiểm tra sau khi đã khóa dòng vai trò và sau kiểm tra `400`.
  - Ghi nhật ký `sua` bảng `vai_tro_quyen` với phần khác biệt dạng danh sách `them`, `bo`, `doi_muc`.
  - **Hiệu lực:** quyền được đọc từ DB mỗi request (bộ nhớ đệm 60 giây, xóa ngay sau commit của thao tác này) nên thay đổi có hiệu lực ở request kế tiếp và KHÔNG thu hồi phiên; menu giao diện của nhân viên đang đăng nhập tự cập nhật khi họ quay lại cửa sổ hoặc sau tối đa 5 phút qua `GET /noi-bo/toi` (spec 09).

### 3.6 Quản lý khách hàng (AD02, `customer.manage`)
Mọi route dưới `/api/v1/noi-bo/khach-hang`; đọc cần mức `xem`, ghi cần `day_du` VÀ người thực hiện thuộc vai trò ADMIN (`dam_bao_la_admin`, như mục 3.4). `{khach_id}` là số nguyên 1..2147483647 (ngoài khoảng là `400 DU_LIEU_KHONG_HOP_LE`; không có hoặc đã xóa tài khoản [DB23] là `404 KHONG_TIM_THAY`).
- **Không bao giờ có** `ho_so_suc_khoe`, `di_ung`, `benh_nen`, `mat_khau_hash` hay bất kỳ trường sức khỏe nào ở mọi phản hồi của nhóm này (spec 03 mục 5.1; schema khai báo từng trường, có test quét khóa và giá trị với khách có hồ sơ sức khỏe thật).
- `GET /noi-bo/khach-hang?q=&trang_thai=&sap_xep=&trang=&kich_thuoc=` -> trang `{id, ho_ten, email, so_dien_thoai, trang_thai, khoa_den, created_at}`. Khách đã xóa không có trong danh sách. `q` tìm tên (không phân biệt dấu, hoa thường), email, số điện thoại: chuỗi giống số điện thoại được đưa về dạng lưu (`+84 902-345-678`, `84902345678` đều tìm ra `0902345678`; một phần số cũng khớp); `%` và `_` là chữ thường. `sap_xep` (mục 5) nhận `created_at` (mặc định `-created_at`, mới đăng ký trước), `ho_ten`, `email`, `so_dien_thoai`; trường khác là `400`.
- `GET /noi-bo/khach-hang/{khach_id}` -> chi tiết: các trường trên cộng `gioi_tinh`, `dong_y_chinh_sach_luc`, `updated_at`, `so_don_hang` (mọi trạng thái).
- `GET /noi-bo/khach-hang/{khach_id}/don-hang?trang=&kich_thuoc=` -> lịch sử mua, mới nhất trước: `{id, ma_don, kenh_ban, trang_thai, trang_thai_tt, tong_tien, created_at}` (tiền dạng chuỗi số). Chỉ đơn có `khach_hang_id` này (không gồm đơn khách lẻ hay của người khác). Cố ý không có người nhận, địa chỉ giao, ghi chú, token truy cập: chi tiết đơn thuộc AD16 (T4.x), khi có API đơn hàng của Admin thì dùng lại ở đây.
- `POST /noi-bo/khach-hang/{khach_id}/khoa` thân tùy chọn `{ly_do?}` (tối đa 300 ký tự, chỉ ghi vào nhật ký, không lưu ở hồ sơ khách) -> chi tiết. `trang_thai = bi_khoa` và thu hồi MỌI phiên của khách ngay: access token đang dùng bị từ chối `403 TAI_KHOAN_BI_KHOA` ở request kế tiếp (guard đọc DB mỗi request), refresh token bị coi là đã thu hồi (`401 CHUA_DANG_NHAP`), đăng nhập bằng mật khẩu đúng nhận `403 TAI_KHOAN_BI_KHOA` còn sai mật khẩu vẫn là `401` như tài khoản bình thường. Khóa dòng khách `FOR UPDATE` TRƯỚC khi thu hồi phiên (thứ tự của QĐ-12); đã khóa thì gọi lại vẫn 200 và không ghi thêm nhật ký.
- `POST /noi-bo/khach-hang/{khach_id}/mo-khoa` -> chi tiết: `trang_thai = hoat_dong`, xóa `khoa_den` (khóa tạm do đoán mật khẩu) và bộ đếm đăng nhập sai. Đã bình thường thì gọi lại vẫn 200, không ghi nhật ký. Lưu ý (giới hạn đã chấp nhận, QĐ-14): access token cấp TRƯỚC lúc khóa dùng lại được nếu mở khóa trước khi nó hết hạn (tối đa `JWT_ACCESS_PHUT` = 15 phút), vì token không tra DB phiên; refresh token đã thu hồi thì vẫn chết.
- Nhật ký `khoa`, `mo_khoa` (bảng `khach_hang`, `ban_ghi_id` = id khách): `gia_tri_moi = {ly_do}` nếu có. Hệ thống không tự ghi số điện thoại, email hay dữ liệu sức khỏe của khách; riêng `ly_do` là văn bản Admin tự nhập nên KHÔNG được kiểm tra nội dung (giao diện nhắc không nhập thông tin cá nhân hay sức khỏe).

### 3.7 Cấu hình hệ thống (AD08, `config.manage`)
Mọi route dưới `/api/v1/noi-bo/cau-hinh`; đọc cần mức `xem`, ghi cần `day_du` VÀ người thực hiện thuộc vai trò ADMIN (`dam_bao_la_admin`, như mục 3.4). Danh sách khóa, kiểu và giới hạn: spec 02 mục 6. Bốn khóa `ai_*` thuộc AD09 nên không có ở đây (`PUT` vào chúng là `404`).
- `GET /noi-bo/cau-hinh` -> `[{khoa, nhom, nhan, mo_ta, kieu, don_vi, toi_thieu, toi_da, truong, gia_tri, phien_ban, nhan_vien_cap_nhat: {id, ma_nhan_vien, ho_ten} | null, updated_at}]`, đã xếp theo nhóm (chủ đề) rồi theo thứ tự hiển thị. `kieu` là `so`, `tien`, `nhom_so` (đối tượng gồm các số, mô tả ở `truong: [{ten, nhan, don_vi, toi_thieu, toi_da}]`) hoặc `gio_lam_viec`. Giao diện dựng ô nhập từ các trường này, backend vẫn kiểm tra lại toàn bộ. Khóa chưa có trong bảng (chưa seed) vẫn được liệt kê với `gia_tri = null`.
- `PUT /noi-bo/cau-hinh/{khoa}` `{gia_tri, phien_ban}` -> một phần tử như trên. Đặt đúng giá trị mới của khóa; ghi `nhan_vien_cap_nhat_id`, `updated_at`; có hiệu lực ngay vì mọi nơi đọc `cau_hinh` mỗi lần dùng.
  - `400 DU_LIEU_KHONG_HOP_LE` (kèm `chi_tiet: [{truong, loi}]`, `truong` dạng `gia_tri` hoặc `gia_tri.<tên trường>`) khi sai kiểu, ngoài khoảng, thiếu hoặc thừa trường, hoặc `phien_ban` sai định dạng.
  - `409 DU_LIEU_DA_THAY_DOI` khi `phien_ban` (dấu vân tay nội dung 16 ký tự hex của giá trị hiện tại, đọc ở `GET`) không còn khớp: Admin khác vừa sửa khóa này. Không ghi gì.
  - Đặt đúng giá trị hiện tại thì trả 200 và không ghi nhật ký. Khóa dòng `cau_hinh` `FOR UPDATE` nên hai Admin sửa cùng khóa được tuần tự hóa.
  - Nhật ký `sua` (bảng `cau_hinh`, `ban_ghi_id` = khóa) với giá trị cũ và mới; khóa chưa có dòng thì ghi `tao` với giá trị cũ `null`.

### 3.8 Nhật ký hệ thống (AD15, `audit.view`)
Chỉ đọc; mọi route dưới `/api/v1/noi-bo/nhat-ky`, mức `xem`.
- `GET /noi-bo/nhat-ky?bang=&ban_ghi_id=&nhan_vien_id=&hanh_dong=&tu_ngay=&den_ngay=&trang=&kich_thuoc=` -> trang `{id, created_at, nhan_vien: {id, ma_nhan_vien, ho_ten} | null, hanh_dong, bang, ban_ghi_id, gia_tri_cu, gia_tri_moi, ip}`, mới nhất trước (`created_at`, rồi `id` giảm dần). `bang`, `ban_ghi_id`, `hanh_dong` khớp chính xác; `tu_ngay`, `den_ngay` là ngày theo giờ Việt Nam, gồm cả hai đầu, trong khoảng 2000-01-01 đến 2100-12-31 (ngoài khoảng hoặc `tu_ngay` lớn hơn `den_ngay` là `400`); các bộ lọc kết hợp bằng AND. `nhan_vien = null` là hệ thống hoặc người chưa xác định (đăng nhập thất bại). Không có email hay số điện thoại của nhân viên.
- `GET /noi-bo/nhat-ky/gia-tri-loc` -> `{bang: [...], hanh_dong: [...]}`: các giá trị đang có trong nhật ký (tối đa 200 mỗi loại), để giao diện dựng ô lọc.
- **Dữ liệu sức khỏe không bao giờ ra khỏi nhật ký (spec 03 mục 5.1, CLAUDE.md quy tắc 7):** với bảng `ho_so_suc_khoe`, `di_ung` chỉ có `bang`, `ban_ghi_id`, hành động, người và thời gian; `gia_tri_cu`, `gia_tri_moi` luôn `null` (bị bỏ ngay lúc ghi, và che lại lần nữa lúc đọc nếu dữ liệu cũ có sót). Mọi giá trị còn lại cũng được che theo tên khóa nhạy cảm lúc đọc (mật khẩu, OTP, token, hash, bệnh nền, thai kỳ, năm sinh, thông tin nhận hoàn tiền...).
- Nhật ký chỉ INSERT: không có route sửa hay xóa.

### 3.9 Quản lý danh mục (AD03, `category.manage`)
Mọi route dưới `/api/v1/noi-bo/danh-muc`; đọc cần mức `xem`, ghi cần `day_du` VÀ người thực hiện thuộc vai trò ADMIN (`dam_bao_la_admin`, như mục 3.4). `{id}` là số nguyên 1..2147483647. Danh mục đã xóa mềm không xuất hiện và là `404`.
- **Nút cây** `DanhMucNut`: `{id, ten, slug, danh_muc_cha_id, anh_url, thu_tu, dang_hien_thi, cap, so_san_pham, con: [DanhMucNut]}`. `cap` là 1 đến 3; `so_san_pham` đếm sản phẩm chưa xóa nằm TRỰC TIẾP trong danh mục đó; `con` đã xếp theo `thu_tu` rồi `id`.
- `GET /noi-bo/danh-muc` -> `[DanhMucNut]`: các danh mục gốc kèm cây con (có cả danh mục đang ẩn `dang_hien_thi = false`, không có danh mục đã xóa).
- `POST /noi-bo/danh-muc` `{ten, danh_muc_cha_id?, anh_url?, dang_hien_thi?}` -> 201 `DanhMucNut`. `slug` tự sinh từ tên (không dấu, gạch ngang); trùng với bất kỳ danh mục nào, kể cả đã xóa mềm, thì thêm hậu tố `-2`, `-3`... Danh mục mới xếp cuối các danh mục cùng cha.
  - `400 DU_LIEU_KHONG_HOP_LE` (`truong = danh_muc_cha_id`) khi danh mục cha không tồn tại hoặc đã ở cấp 3 (từ chối cấp 4).
  - `409 TRUNG_DU_LIEU` (`chi_tiet.truong = "ten"`) khi tên trùng một danh mục cùng cha (không phân biệt hoa thường và dấu).
- `PATCH /noi-bo/danh-muc/{id}` `{ten?, anh_url?, dang_hien_thi?}` (trường lạ là `400`) -> `DanhMucNut`. **Đổi tên không đổi `slug`** (đường dẫn công khai ổn định). `dang_hien_thi = false` ẩn danh mục và cả cây con khỏi menu và trang danh mục của khách (áp dụng ở T2.4), KHÔNG xóa gì và có thể bật lại.
- `PUT /noi-bo/danh-muc/{id}/vi-tri` `{danh_muc_cha_id, vi_tri}` -> `[DanhMucNut]` (cả cây mới). Đặt danh mục vào dưới `danh_muc_cha_id` (`null` là gốc) tại chỉ số `vi_tri` (từ 0; lớn hơn số anh em thì đặt cuối). Dùng cho cả sắp xếp lại trong cùng cha lẫn chuyển sang cha khác (kéo thả); `thu_tu` của anh em ở cha cũ và cha mới được đánh lại liên tục từ 0.
  - `400 DU_LIEU_KHONG_HOP_LE` (`truong = danh_muc_cha_id`) khi chuyển vào chính nó hoặc danh mục con cháu của nó (vòng), hoặc khiến bất kỳ nhánh nào vượt 3 cấp (tính cả cây con đang mang theo).
  - `409 TRUNG_DU_LIEU` khi tên trùng một danh mục cùng cha mới.
- `DELETE /noi-bo/danh-muc/{id}` -> 204. Xóa mềm (`deleted_at`), `slug` vẫn được giữ chỗ.
  - `409 DANH_MUC_CON_SAN_PHAM` khi còn sản phẩm chưa xóa nằm trong danh mục.
  - `409 DANH_MUC_CON_DANH_MUC` khi còn danh mục con chưa xóa (xóa từng nhánh từ lá lên; muốn tạm ẩn cả nhánh thì dùng `dang_hien_thi`).
- Mọi thao tác ghi thay đổi cây được tuần tự hóa bằng một khóa tư vấn PostgreSQL (kiểm tra cấp và vòng cần thấy cây nhất quán), xóa khóa dòng danh mục `FOR UPDATE` trước khi đếm sản phẩm; nhật ký `tao`, `sua`, `xoa` (bảng `danh_muc`) kèm giá trị cũ/mới của các trường đã đổi.

### 3.10 Dữ liệu dùng chung: thương hiệu, nhà sản xuất, hoạt chất (AD05, `master_data.manage`)
Ba nhóm route cùng một khuôn: `/api/v1/noi-bo/thuong-hieu`, `/api/v1/noi-bo/nha-san-xuat`, `/api/v1/noi-bo/hoat-chat`. Đọc cần mức `xem` (dược sĩ có mức `chi_xem` nên đọc được); ghi cần `day_du` (mặc định chỉ Admin; quyền này không thuộc nhóm chỉ-ADMIN nên AD18 có thể ủy quyền, vì vậy không có chốt thêm theo vai trò).
- `GET /noi-bo/<nhóm>?q=&sap_xep=&trang=&kich_thuoc=` -> trang. `q` tìm tên (hoạt chất: cả `ten_khac`) không phân biệt dấu/hoa thường; `%` và `_` là chữ thường. `sap_xep`: `ten` (mặc định), `created_at`, `so_san_pham`; `-` đảo chiều. `GET /noi-bo/<nhóm>/{id}` -> một phần tử.
- Phần tử: thương hiệu `{id, ten, logo_url, created_at, so_san_pham}`; nhà sản xuất `{id, ten, quoc_gia, created_at, so_san_pham}`; hoạt chất `{id, ten, ten_khac, mo_ta, created_at, so_san_pham}`. `so_san_pham` đếm sản phẩm gắn với bản ghi (với hoạt chất: số dòng `thanh_phan`), tính cả sản phẩm đã xóa mềm vì khóa ngoại vẫn tham chiếu. Không có số liệu nào về hồ sơ dị ứng của khách.
- `POST /noi-bo/<nhóm>` (201), `PATCH /noi-bo/<nhóm>/{id}` (chỉ trường gửi lên; trường lạ là `400`), `DELETE /noi-bo/<nhóm>/{id}` (204).
  - Tên: bỏ khoảng trắng đầu cuối và gộp khoảng trắng liên tiếp; không rỗng; tối đa 150 (thương hiệu), 200 (nhà sản xuất, hoạt chất) ký tự.
  - `409 TRUNG_DU_LIEU` (`chi_tiet.truong = "ten"`) khi trùng không phân biệt hoa thường và dấu: thương hiệu và hoạt chất theo tên; nhà sản xuất theo cặp (tên, quốc gia) và `quoc_gia` trống được coi là một giá trị (ràng buộc unique của DB bỏ qua NULL nên việc này do service kiểm tra, có xử lý đua nhau).
  - `logo_url`: để trống hoặc là đường dẫn bắt đầu bằng `/` hoặc `https://` hoặc `http://`, tối đa 500 ký tự (không nhận `javascript:` và các scheme khác). `ten_khac` tối đa 1000 ký tự, `mo_ta` tối đa 2000, `quoc_gia` tối đa 100.
  - `DELETE` xóa cứng bản ghi chưa được tham chiếu; đang được tham chiếu (sản phẩm, thành phần, tương tác, dị ứng...) thì `409 DU_LIEU_DANG_DUOC_SU_DUNG` với thông điệp chung, không nói bản ghi nào đang dùng nó (hoạt chất có thể nằm trong dị ứng của khách, là dữ liệu Admin không được thấy).
  - Nhật ký `tao`, `sua`, `xoa` với bảng tương ứng.

## 4. Định dạng phản hồi và lỗi
- **Thành công:** trả đối tượng hoặc trang dữ liệu (mục 5).
- **Lỗi:** luôn trả dạng:
  ```json
  {"ma_loi": "HET_HANG", "thong_diep": "Sản phẩm Paracetamol 500mg chỉ còn 3 viên", "chi_tiet": {"san_pham_id": 12, "con_lai": 3}}
  ```

**Mã lỗi dùng chung** (thêm mã mới vào bảng này khi tạo):

| HTTP | `ma_loi` | Khi nào |
|---|---|---|
| 400 | `DU_LIEU_KHONG_HOP_LE` | Validate thất bại; `chi_tiet` là danh sách `{truong, loi}` |
| 401 | `CHUA_DANG_NHAP`, `TOKEN_HET_HAN`, `SAI_THONG_TIN_DANG_NHAP` | |
| 403 | `KHONG_CO_QUYEN`, `TAI_KHOAN_BI_KHOA`, `PHAI_DOI_MAT_KHAU`, `TU_DUYET_KHONG_DUOC`, `TU_THAY_DOI_KHONG_DUOC` (Admin tự khóa, tự xóa, tự đổi vai trò, tự đặt lại mật khẩu) | |
| 404 | `KHONG_TIM_THAY` | Kể cả khi tài nguyên tồn tại nhưng thuộc khách khác |
| 405 | `PHUONG_THUC_KHONG_DUOC_PHEP` | Gọi sai phương thức HTTP; giữ header `Allow` |
| 409 | `HET_HANG`, `CHUYEN_TRANG_THAI_KHONG_HOP_LE`, `DA_CO_NGUOI_XU_LY`, `GIA_DA_THAY_DOI`, `TRUNG_DU_LIEU`, `PHAI_CON_ADMIN`, `DU_LIEU_DA_THAY_DOI` (khóa lạc quan: bản sửa dựa trên dữ liệu đã bị người khác đổi), `DANH_MUC_CON_SAN_PHAM`, `DANH_MUC_CON_DANH_MUC` (xóa danh mục còn danh mục con), `DU_LIEU_DANG_DUOC_SU_DUNG` (xóa thương hiệu, nhà sản xuất, hoạt chất đang được tham chiếu) | |
| 422 | `THUOC_KE_DON_KHONG_VAO_GIO`, `VUOT_SO_LUONG_TOI_DA`, `MA_GIAM_GIA_KHONG_HOP_LE`, `QUA_THOI_HAN_DOI_TRA`, `HOAN_VUOT_SO_DA_TRA`, `OTP_SAI`, `OTP_HET_HAN`, `MAT_KHAU_CU_SAI` | Vi phạm quy tắc nghiệp vụ |
| 429 | `QUA_GIOI_HAN` | Giới hạn tần suất; kèm header `Retry-After` |
| 502 | `LOI_DOI_TAC` | Cổng thanh toán hoặc vận chuyển lỗi |
| khác | `LOI_HTTP` | Lỗi HTTP 4xx khác do framework phát sinh (ví dụ 413); giữ nguyên status. Lỗi 5xx khác quy về `LOI_HE_THONG` |
| 500 | `LOI_HE_THONG` | Không lộ stack trace; `chi_tiet` là `{"request_id": "..."}`, log có `request_id` |

**Quy ước thực thi** (`core/loi.py`, `core/middleware.py`):
- Danh sách mã lỗi trong code (`MA_LOI`) phải khớp bảng này. Test `test_bang_ma_loi_khop_spec_06` báo lỗi nếu lệch; thêm mã mới thì sửa cả hai nơi.
- `LoiNghiepVu(ma_loi, thong_diep, chi_tiet=...)` tự lấy HTTP status từ bảng. `chi_tiet` luôn có mặt trong phản hồi (giá trị `null` nếu không có).
- Lỗi validate (400): `chi_tiet` là danh sách `{"truong": "dong.1.so_luong", "loi": "Bắt buộc nhập"}`. `truong` là đường dẫn phân cách bằng dấu chấm (bỏ phần `body`/`query`), JSON hỏng thì `truong = "body"`.
- `chi_tiet` có thể chứa `Decimal`, `date`, model Pydantic: handler tự đổi sang JSON. Tiền nên truyền bằng model có trường `Tien` để ra dạng `"125000.00"` (đưa `Decimal` thẳng vào thì ra `"125000"`).
- Lỗi không bắt được được ghi log JSON (có stack trace và `request_id`) rồi trả 500; không ném lại cho server. Log che các dòng `DETAIL:`/`HINT:`/`CONTEXT:` của PostgreSQL và ẩn tham số SQL, vì chúng chứa giá trị dữ liệu người dùng.
- Mọi phản hồi (kể cả lỗi) có header `X-Request-ID`. Client có thể tự gửi header này (8–64 ký tự `A-Za-z0-9._-`), không hợp lệ thì server tự sinh. Trình duyệt đọc được header nhờ `Access-Control-Expose-Headers`.
- Ngoại lệ về định dạng: `GET /api/v1/health` dùng body riêng (mục 2).

## 5. Phân trang, lọc, sắp xếp
- **Tham số:**
  - Phân trang: `trang` (từ 1, tối đa 1.000.000), `kich_thuoc` (mặc định 20, tối đa 100).
  - Sắp xếp: `sap_xep=-created_at` (dấu `-` là giảm dần; chỉ nhận trường nằm trong danh sách cho phép của endpoint).
  - Lọc: tên trường làm tham số, ví dụ `trang_thai=cho_xac_nhan&tu_ngay=2026-10-01&den_ngay=2026-10-15`.
- **Phản hồi:** `{"du_lieu": [...], "tong": 135, "trang": 1, "kich_thuoc": 20}`.

## 6. Idempotency
- `POST /api/v1/toi/don-hang` và các API tạo giao dịch thanh toán/hoàn tiền nhận header `Idempotency-Key` (UUID do client sinh).
- Server lưu khóa cùng kết quả 24 giờ trong bộ nhớ đệm (bảng tạm hoặc cache in-process cho đồ án). Gửi lại cùng khóa thì trả lại đúng kết quả cũ.
- IPN và webhook chống xử lý trùng bằng mã giao dịch của đối tác (spec 08).

## 7. Upload file
- **Ảnh sản phẩm, banner, bài viết** (công khai): `POST /api/v1/noi-bo/tep` (multipart). Trả `url` công khai.
- **Ảnh đơn thuốc, ảnh/video đổi trả** (riêng tư):
  - Upload kèm request nghiệp vụ.
  - Lưu khóa file trong jsonb (`anh_don_thuoc`, `anh`).
  - Đọc qua `GET /api/v1/.../tep/{khoa}` để nhận URL ký có hạn 10 phút. Chỉ chủ sở hữu hoặc người được phép (spec 03 mục 6) nhận được URL.
- **Kiểm tra file:** kiểu MIME thật (đọc magic bytes); ảnh tối đa 5 MB (jpeg, png, webp); video đổi trả tối đa 30 MB (mp4); đổi tên file thành UUID.

## 8. Webhook và IPN
| Endpoint | Đối tác | Xử lý |
|---|---|---|
| `GET /api/v1/webhook/vnpay-ipn` | VNPay | Kiểm chữ ký → kiểm số tiền → chống trùng → HT04 → trả JSON `RspCode` theo tài liệu VNPay |
| `POST /api/v1/webhook/momo-ipn` | MoMo | Kiểm chữ ký → kiểm số tiền → chống trùng → HT04 → trả đúng mã phản hồi MoMo yêu cầu |
| `POST /api/v1/webhook/ghn` | GHN | Kiểm token → ghi `van_don.du_lieu_webhook` → ánh xạ trạng thái → HT05/HT06 |

- Trang "kết quả thanh toán" phía frontend **không** tin tham số trên URL trả về. Trang này hỏi lại backend trạng thái đơn.

## 9. SSE và WebSocket
- **Chat AI:** `POST /api/v1/tu-van/chat` với body `{ma_phien, noi_dung}`, trả `text/event-stream`. Các loại sự kiện:
  - `van_ban` (đoạn chữ).
  - `the_san_pham` (danh sách sản phẩm gợi ý).
  - `chuyen_duoc_si`.
  - `nguy_hiem`.
  - `ket_thuc` (kèm `tin_nhan_id`).
  - `loi`.
- **Chat dược sĩ:** WebSocket `/api/v1/tu-van/ws?ma_phien=...`.
  - Xác thực bằng access token gửi trong message đầu tiên, sau đó server kiểm tra quyền vào phiên.
  - Message JSON `{loai: "tin_nhan"|"dang_go"|"he_thong", ...}`.
  - Hub kết nối giữ trong bộ nhớ process (đồ án chạy 1 process API; muốn chạy nhiều process thì cần Redis pub/sub, ngoài phạm vi).

## 10. OpenAPI và client frontend
- Mọi route khai báo `response_model` và schema lỗi.
- Frontend chạy `npm run gen:api` (dùng `openapi-typescript`) để sinh `src/api/schema.d.ts`, gọi qua `openapi-fetch`. Không tự viết type trùng với API.
- Đổi schema API thì phải sinh lại type và sửa lỗi TypeScript trong cùng task.
