# 12. Nhật ký quyết định

Mỗi quyết định ảnh hưởng đến thiết kế, nghiệp vụ hoặc công nghệ được ghi một mục theo mẫu dưới đây. Quyết định mới thêm vào **cuối file**, không sửa mục cũ. Nếu đổi ý thì viết mục mới và ghi "Thay thế QĐ-xx".

```
## QĐ-xx: <tiêu đề ngắn> (YYYY-MM-DD, task Tx.y)
- Bối cảnh: ...
- Quyết định: ...
- Hệ quả: ... (file spec / code bị ảnh hưởng)
```

## QĐ-01: Phạm vi 3 tác nhân, 1 nhà thuốc = 1 kho (2026-10-15)
- **Bối cảnh:** Đồ án kiểu Long Châu nhưng thu gọn phạm vi.
- **Quyết định:**
  - 3 tác nhân Khách hàng / Nhân viên / Quản trị, chia thành 5 nhóm người dùng.
  - Nhân viên chia vai trò bằng RBAC; mỗi nhân viên có 1 vai trò.
  - Không làm chi nhánh hay chuyển kho.
- **Hệ quả:** spec 00, 03. `nhan_vien.vai_tro_id` giữ quan hệ N-1.

## QĐ-02: ERD đã chỉnh sửa là nguồn sự thật (2026-10-15)
- **Bối cảnh:** ERD gốc có 1 lỗi cú pháp và thiếu chỗ lưu một số nghiệp vụ (biệt trữ, thẻ kho, vận đơn trả hàng, hoàn tiền...).
- **Quyết định:** dùng `docs/database/ERD_da_chinh_sua.dbml` (65 bảng). Mọi thay đổi ghi `[DBxx]`, đối chiếu sheet "Đánh giá Database" trong file Excel.
- **Hệ quả:** spec 02. Lệnh `/doi-schema`.

## QĐ-03: Backend FastAPI + SQLAlchemy async (2026-10-15)
- **Bối cảnh:** Sheet chỉ ghi "Python".
- **Quyết định:**
  - FastAPI, SQLAlchemy 2 async (asyncpg), Alembic, Pydantic v2, `uv`.
  - Job nền: APScheduler ở process riêng.
  - Chat dược sĩ: WebSocket. Chat AI: SSE.
- **Hệ quả:** spec 01, 06; `backend/CLAUDE.md`.

## QĐ-04: Frontend React + Vite + Ant Design (2026-10-15)
- **Quyết định:**
  - TypeScript, Ant Design (`vi_VN`), TanStack Query, React Router, Zustand.
  - Client API sinh từ OpenAPI (`openapi-typescript` + `openapi-fetch`).
  - Một ứng dụng duy nhất chia 3 khu theo đường dẫn.
- **Hệ quả:** spec 09; `frontend/CLAUDE.md`.

## QĐ-05: Claude API cho LLM, BGE-M3 tự host cho embedding (2026-10-15)
- **Quyết định:**
  - Model `claude-opus-5-5` (biến `CLAUDE_MODEL`), đặt `effort` rõ ràng cho từng tác vụ.
  - Bật `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) để tự chạy lại khi bị bộ lọc an toàn từ chối.
  - Embedding `BAAI/bge-m3`, 1024 chiều, khớp `vector(1024)` của ERD.
- **Hệ quả:** spec 07. Đổi model là quyết định chi phí của nhóm, phải ghi một QĐ mới.

## QĐ-06: Mọi tích hợp ngoài có adapter giả (2026-10-15)
- **Quyết định:**
  - VNPay, MoMo, GHN, SMS/email đi qua interface có bản giả chạy offline.
  - Dev và test mặc định dùng bản giả; sandbox thật bật bằng biến môi trường.
- **Hệ quả:** spec 08. Có thể demo đầy đủ luồng mà không cần tài khoản đối tác.

## QĐ-07: Lịch sử chat gửi lại Claude chỉ gồm text (2026-10-15)
- **Bối cảnh:** `tin_nhan` chỉ lưu nội dung text. Trên Opus 5.5, thinking blocks gắn với đúng hội thoại đã tạo ra chúng.
- **Quyết định:**
  - Giữa các lượt, chỉ gửi lại text của các lượt trước.
  - Trong cùng một lượt có gọi tool, append nguyên `response.content`.
  - System prompt và danh sách tool cố định.
- **Hệ quả:** spec 07 mục 2. Không cần cột lưu nội dung thô của Claude.

## QĐ-08: Access token chỉ ở bộ nhớ trình duyệt, làm mới bằng cookie refresh (2026-10-15, task T0.6, T0.7)
- **Quyết định:**
  - Frontend giữ access token và hồ sơ trong store Zustand, KHÔNG persist (không localStorage/sessionStorage). Tải lại trang thì lấy lại token bằng refresh token trong cookie httpOnly.
  - Client API gặp 401 thì làm mới đúng một lần (nhiều request lỗi cùng lúc dùng chung một lần làm mới) rồi gọi lại request gốc đúng một lần; gọi lại vẫn 401 hoặc làm mới thất bại thì đăng xuất. Chỉ làm mới khi request gốc có kèm token; các endpoint `dang-nhap`, `dang-ky`, `lam-moi`, `dang-xuat`, `quen-mat-khau`, `otp` không bao giờ kích hoạt làm mới.
  - Thân phản hồi đăng nhập/làm mới là `{"access_token": "<jwt>"}` (spec 06 mục 3).
  - Hàm tạo/kiểm tra JWT (`core/bao_mat.py`) làm ở T0.6 để fixture đăng nhập của test dùng token thật; endpoint đăng nhập và refresh token vẫn ở T1.x.
- **Hệ quả:** spec 06 mục 3; `frontend/CLAUDE.md`; T1.2, T1.3 phải trả đúng thân phản hồi trên.

## QĐ-09: Seed không hoàn tác chỉnh sửa của Admin; Admin đầu tiên cần mật khẩu mạnh (2026-10-15, task T0.5)
- **Bối cảnh:** rà soát nghiệp vụ T0.5 tìm thấy seed ghi đè việc Admin gán/bỏ quyền (AD18) và chấp nhận mật khẩu mẫu công khai của `.env.example` cho Admin.
- **Quyết định:**
  - Seed chỉ cấp mặc định cho quyền MỚI; quyền đã có giữ nguyên cách gán hiện tại. Danh mục `quyen` vẫn đồng bộ theo `quyen.yaml`. `vai_tro` và `cau_hinh` chỉ thêm cái còn thiếu.
  - Admin đầu tiên: mật khẩu tối thiểu 12 ký tự (chặt hơn mức chung 8), không được bắt đầu bằng `doi-` (giá trị mẫu); `JWT_SECRET` cũng không được là giá trị mẫu.
  - `--mau` chỉ chạy với CSDL ở máy cục bộ, trừ khi có `--cho-phep-may-chu-khac`; SKU và số lô mẫu có tiền tố `MAU-`.
- **Hệ quả:** spec 02 mục 6; `backend/CLAUDE.md`.

## QĐ-10: Phân luồng ba khu và guard quyền trên UI (2026-10-15, task T0.7)
- **Quyết định:**
  - Route guard khu nội bộ dùng mức `xem` (quyền chỉ xem vẫn vào được trang xem); nút thao tác bọc `<YeuCauQuyen kieu="nut">` mức đầy đủ và ẩn hẳn khi thiếu.
  - Phiên của khách không được coi là đã đăng nhập nội bộ. Chưa đăng nhập nội bộ thì mọi route `/nhan-vien` và `/quan-tri` chuyển tới `/nhan-vien/dang-nhap`.
  - Admin vào `/nhan-vien` bị chuyển sang `/quan-tri`; không phải Admin vào `/quan-tri` thấy 403. Mỗi trang con vẫn kiểm tra mã quyền riêng.
  - Bảng route và menu nằm ở `khu/nhan-vien/menu.ts`, `khu/quan-tri/menu.ts`, `khu/cua-hang/trang.ts`, có test đối chiếu từng dòng với spec 09 mục 2 và với `quyen.yaml`.
- **Hệ quả:** spec 09; `frontend/CLAUDE.md`.

## QĐ-11: Đăng nhập khách, phiên và giới hạn đã chấp nhận (2026-10-15, task T1.2)
- **Quyết định:**
  - Refresh token là chuỗi ngẫu nhiên 256 bit, DB chỉ lưu SHA-256; cookie `refresh_token` có `HttpOnly; SameSite=Lax; Secure`, `Path=/api/v1/auth`; xoay vòng mỗi lần làm mới; dùng lại token đã thu hồi thì thu hồi toàn bộ phiên (spec 06 mục 3, 3.2). Khóa dòng phiên bằng `FOR UPDATE` nên hai lần làm mới đồng thời cùng một token chỉ một bên thắng.
  - **Giới hạn đã chấp nhận 1, làm mới đồng thời:** vì quy tắc "dùng lại là bị thu hồi hết", hai lần làm mới cùng lúc bằng một cookie (nhiều tab mở cùng lúc, hoặc trình duyệt khôi phục nhiều tab sau khi khởi động) sẽ làm bên đến sau bị coi là dùng lại và đăng xuất mọi thiết bị. Không thêm "thời gian ân hạn" ở backend (sẽ làm yếu phát hiện trộm token). Thay vào đó frontend tuần tự hóa việc làm mới giữa mọi tab bằng Web Locks API (`api/xacThuc.ts`) và chỉ làm mới một lần khi tải trang (`api/khoiPhuc.ts`). Đã kiểm chứng trên Chromium: 4 tab tải cùng lúc, bật Web Locks thì 4/4 còn đăng nhập, tắt thì 1/4. Trình duyệt không có Web Locks vẫn chịu rủi ro này.
  - **Giới hạn đã chấp nhận 2, dò tài khoản qua khóa tạm:** sai mật khẩu liên tục với số CÓ tài khoản sẽ dẫn tới `403 TAI_KHOAN_BI_KHOA` (khóa tạm) còn số KHÔNG có tài khoản mãi là `401`, nên kẻ thử nhiều lần có thể phân biệt. Khóa tạm là yêu cầu của KVL10 và cần báo người dùng thật biết mình bị khóa, nên chấp nhận; giảm thiểu bằng giới hạn 20 lần mỗi IP mỗi 10 phút và việc khóa tạm không kéo dài thêm khi tiếp tục thử. Mọi phản hồi khác (sai mật khẩu, số lạ, đã xóa) giống hệt nhau.
  - Frontend giữ thêm MỘT khóa `localStorage` là `phien_goi_y` (`khach` hoặc `noi_bo`), không phải token hay hồ sơ: chỉ để biết có nên thử làm mới khi tải trang, nhờ đó khách vãng lai không gọi API thừa. Cập nhật QĐ-08: "không persist token và hồ sơ", vẫn đúng.
  - `?tiep=` sau khi đăng nhập chỉ nhận đường dẫn nội bộ (một dấu `/` đầu, không `//`, `\`, ký tự điều khiển, không về chính trang đăng nhập/đăng ký/quên mật khẩu) để tránh open redirect.
  - Endpoint đặt lại mật khẩu đặt tên `POST /auth/dat-lai-mat-khau` (QĐ-08 ghi `quen-mat-khau` cho danh sách không tự làm mới; frontend dùng `dat-lai-mat-khau`).
- **Hệ quả:** spec 01 (bảng biến môi trường: `COOKIE_SECURE`), spec 06 mục 3.2; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

## QĐ-12: Xác thực nhân viên, RBAC và nhật ký (2026-10-15, task T1.3)
- **Quyết định:**
  - **Ba route xác thực công khai nằm trong `/api/v1/noi-bo/auth/`** (`dang-nhap`, `lam-moi`, `dang-xuat`): ngoại lệ duy nhất của quy tắc "route `/noi-bo` phải có `yeu_cau_quyen`", khai báo tường minh ở `CONG_KHAI` của registry. `doi-mat-khau` thì cần `profile.self`.
  - **Đổi mật khẩu thu hồi mọi phiên cũ rồi cấp phiên mới cho thiết bị đang đổi** (không đẩy người đang đổi ra màn đăng nhập); mọi thiết bị khác phải đăng nhập lại. Đoán mật khẩu cũ qua chức năng này được đếm như đăng nhập sai và khi khóa thì thu hồi mọi phiên, nên kẻ cầm access token đánh cắp không dò được mật khẩu.
  - **Khóa tạm do đoán mật khẩu KHÔNG thu hồi phiên đang chạy của chủ tài khoản, cả lúc đăng nhập lẫn lúc làm mới** (nếu thu hồi, kẻ chỉ cần gửi sai 5 lần là đăng xuất được người khác). Làm mới lúc đang khóa tạm: `403 TAI_KHOAN_BI_KHOA` kèm `thu_lai_sau_giay`, không xoay vòng, không xóa cookie, hết khóa thì dùng tiếp token cũ. Khóa do Admin (AD01, T1.4) hoặc xóa mềm thì thu hồi mọi phiên và xóa cookie. (Bản đầu của T1.2/T1.3 làm mới xong mới kiểm tra khóa nên khóa tạm cũng làm mất mọi phiên, mâu thuẫn với quyết định này; rà soát nghiệp vụ phát hiện và đã sửa.)
  - **Thứ tự khóa dòng: tài khoản trước, phiên sau** ở mọi luồng đụng cả hai (đăng nhập, làm mới, đổi mật khẩu, đặt lại mật khẩu, khóa tài khoản). Làm mới từng chỉ khóa dòng phiên nên chạy đồng thời với đổi/đặt lại mật khẩu thì hai bên giữ khóa chéo nhau và Postgres báo deadlock (đã tái hiện bằng test).
  - **Access token đã cấp còn dùng được tới khi hết hạn (tối đa `JWT_ACCESS_PHUT` = 15 phút)** sau khi đổi mật khẩu hoặc thu hồi phiên, vì token không tra DB phiên. Chấp nhận để giữ token ngắn hạn không trạng thái; riêng trạng thái tài khoản (khóa, xóa mềm), vai trò và quyền được đọc từ DB mỗi request nên có hiệu lực ngay.
  - **Mức quyền `chi_xem` chỉ cho thao tác đọc:** thao tác ghi luôn đòi `day_du` ngay trong `yeu_cau_quyen`, không phụ thuộc người viết route khai báo đúng `muc`. `gioi_han` lạ coi là chỉ xem.
  - **`ke_ca_chua_doi_mat_khau`**: chỉ `GET /noi-bo/toi` và `POST /noi-bo/auth/doi-mat-khau` được miễn việc bắt đổi mật khẩu; test registry giữ danh sách này cố định.
  - **Nhật ký** (`core/nhat_ky.py`): luôn che giá trị của khóa chứa `mat_khau`, `password`, `otp`, `token`, `secret`, `hash`, `benh_nen`, `di_ung`, `suc_khoe`, `khoa_ma_hoa` (kể cả khi người gọi quên), tiền ghi dạng chuỗi (không qua float), số điện thoại chỉ ghi dạng che. Ghi: đăng nhập thành công, khóa tạm (đúng một lần lúc bị khóa), đổi mật khẩu, sửa hồ sơ. Đăng nhập thất bại thường không ghi để kẻ dò không làm phình bảng.
  - **Giới hạn:** bảng `nhat_ky_he_thong` "chỉ INSERT" hiện chỉ được bảo đảm bằng việc ứng dụng không có route sửa/xóa, chưa có trigger chặn UPDATE/DELETE ở DB (cần migration mới qua `/doi-schema`, ghi ở "Việc phát sinh").
  - Cookie refresh nhân viên tên `refresh_token_noi_bo`, `Path=/api/v1/noi-bo/auth`; đăng nhập nội bộ dùng email; nhân viên không có luồng "quên mật khẩu" tự phục vụ (Admin đặt lại ở T1.4).
- **Hệ quả:** spec 03 mục 8, spec 06 mục 3.3, spec 09 mục 1, spec 10 mục 3; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

## QĐ-13: Quản lý nhân viên, vai trò và phân quyền (2026-10-15, task T1.4)
- **Quyết định:**
  - **Mã lỗi mới `TU_THAY_DOI_KHONG_DUOC` (403)** cho Admin tự khóa, tự xóa, tự đổi vai trò, tự đặt lại mật khẩu của mình (tách khỏi `TU_DUYET_KHONG_DUOC` của phiếu kho). Mất Admin hoạt động cuối cùng là `409 PHAI_CON_ADMIN`.
  - **Luôn còn ≥ 1 Admin hoạt động được bảo đảm dưới đồng thời:** mỗi thao tác khóa dòng đích và MỌI dòng Admin chưa xóa trong một câu `ORDER BY id FOR UPDATE`, rồi mới đếm. Nếu chỉ khóa dòng đích thì hai Admin cùng khóa nhau vẫn qua được kiểm tra của nhau và hệ thống không còn Admin nào (đã tái hiện và có test hai session thật).
  - **Vai trò ADMIN bất biến qua AD18** (`409 PHAI_CON_ADMIN`); `profile.self` bắt buộc ở mức đầy đủ cho mọi vai trò (nếu không nhân viên không tự đổi mật khẩu được và bị kẹt ở màn bắt đổi); `content.professional.edit` và `content.approve` chỉ gán được cho PHARMACIST (spec 03 mục 7: Admin không sửa nội dung chuyên môn).
  - **18 quyền mà ma trận spec 03 chỉ cấp cho ADMIN không gán được cho vai trò khác qua AD18** (rà soát nghiệp vụ T1.4, M1 và M2). Bản đầu chỉ chặn hai mã `content.*`, nên Admin cấu hình cho kho `staff.manage` thì kho tự tạo tài khoản ADMIN hoặc đặt lại mật khẩu một Admin (đã chạy thử); cấp `role.manage` thì kho tự thêm `stock_doc.approve`/`refund.confirm` cho vai trò của mình; cấp `refund.confirm` cho dược sĩ thì một người vừa duyệt đổi trả vừa xác nhận hoàn tiền, làm giả định "mỗi nhân viên một vai trò nên đã tách nhiệm vụ" ở spec 03 mục 7 không còn đúng. Quy tắc: quyền nào ma trận chỉ cấp cho ADMIN thì chỉ ADMIN giữ (danh sách đọc từ `quyen.yaml`, thiếu file thì lỗi chứ không bỏ qua). Hệ quả: AD18 chỉ điều chỉnh những quyền đã thuộc về vai trò nghiệp vụ (dược sĩ, kho). Muốn ủy quyền một chức năng quản trị cho nhân viên thì phải sửa ma trận ở spec 03 trước.
  - **Lớp phòng thủ thứ hai:** mọi thao tác ghi của AD01 và AD18 còn đòi người thực hiện thuộc vai trò ADMIN (`core.phan_quyen.dam_bao_la_admin`, `403 KHONG_CO_QUYEN`), để dữ liệu cấu hình sai (gán thẳng vào DB, bỏ qua AD18) không thành quyền tạo Admin. Hệ quả: luật "luôn còn ≥ 1 Admin hoạt động" ở AD01 chỉ còn đạt được khi người thực hiện vừa mất hoạt động giữa chừng (đua nhau), vẫn giữ làm bất biến.
  - **Khóa lạc quan khi lưu phân quyền** (rà soát M3): `PUT /vai-tro/{ma}/quyen` thay TOÀN BỘ nên một trang mở từ trước sẽ ngầm cấp lại quyền Admin khác vừa gỡ (hộp xác nhận chỉ liệt kê thay đổi của chính người lưu). Đọc trả `phien_ban`, lưu phải gửi lại, lệch thì `409 DU_LIEU_DA_THAY_DOI`; giao diện tải lại bản mới và giữ các mục người dùng đã đổi. Chọn phiên bản dạng dấu vân tay nội dung (không có cột mới, không cần migration) thay vì cột số thứ tự.
  - **Đổi vai trò của một nhân viên thu hồi mọi phiên của họ; đổi quyền của một vai trò KHÔNG thu hồi phiên.** Quyền được đọc từ DB ở mỗi request nên quyền mới có hiệu lực ở request kế tiếp (cache 60 giây được xóa sau commit); giao diện của người đang đăng nhập cập nhật menu qua `GET /noi-bo/toi` khi focus lại cửa sổ hoặc sau tối đa 5 phút. Không thu hồi phiên hàng loạt chỉ vì chỉnh một quyền để tránh đẩy cả vai trò ra đăng nhập lại.
  - **Mật khẩu tạm** 12 ký tự từ CSPRNG, chỉ trả trong phản hồi tạo/đặt lại mật khẩu, DB chỉ lưu hash, không vào nhật ký, giao diện hiện đúng một lần trong hộp thoại và xóa khỏi DOM khi đóng. Không có cách xem lại; quên thì Admin đặt lại.
  - **Email nhân viên là duy nhất không phân biệt hoa thường, kể cả với tài khoản đã xóa mềm** (tránh người cũ đăng nhập lại hay lẫn nhật ký); hai Admin tạo cùng email cùng lúc: bên thua nhận `409 TRUNG_DU_LIEU` nhờ savepoint chứ không phải 500.
  - Không có xóa cứng nhân viên: chứng từ, phiếu và nhật ký cũ vẫn trỏ tới người lập.
  - Id trong path dùng `IdInt`/`IdBigInt` (`core/tham_so.py`): id ngoài khoảng của cột là 400.
- **Hệ quả:** spec 03 mục 7, 8; spec 06 mục 3.4, 3.5 và bảng mã lỗi; spec 09 mục 2.3; spec 10 mục 3; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

## QĐ-14: Quản lý khách hàng của Admin (2026-10-15, task T1.5)
- **Quyết định:**
  - **Admin không bao giờ nhận dữ liệu sức khỏe qua AD02, bảo đảm bằng schema chứ không bằng lọc:** `schemas_quan_tri_khach.py` khai báo từng trường (không dùng chung schema của khách hay `model_validate` toàn bộ dòng). Test quét mọi khóa JSON và mọi giá trị (bệnh nền, ghi chú dị ứng, tên hoạt chất) ở danh sách, chi tiết, lịch sử mua và phản hồi khóa với một khách có hồ sơ sức khỏe thật. Thêm trường vào các schema này là quyết định có chủ ý.
  - **Lịch sử mua là bản tóm tắt** (mã đơn, kênh, trạng thái đơn và thanh toán, tổng tiền, ngày đặt), không có người nhận, địa chỉ giao, ghi chú hay token truy cập. Spec 03 mục 6 cho Admin xem mọi đơn, nhưng chi tiết đơn là việc của AD16; trang khách chỉ cần biết khách đã mua gì. Hiện đọc thẳng `don_hang`, khi có API đơn hàng của Admin (T4.x) thì dùng lại.
  - **Khóa khách thu hồi mọi phiên và có hiệu lực ngay** (guard đọc DB mỗi request; QĐ-12). Khóa dòng khách trước, phiên sau, nên không deadlock với đăng nhập, làm mới, đặt lại mật khẩu. Lý do khóa (không bắt buộc, tối đa 300 ký tự) chỉ ghi vào nhật ký hệ thống, không thêm cột vào hồ sơ khách (không đổi schema). Chưa gửi thông báo cho khách bị khóa (KTV13 chưa làm).
  - **Giới hạn đã chấp nhận (rà soát T1.5, L2):** khóa rồi mở khóa trong vòng `JWT_ACCESS_PHUT` (15 phút) thì access token cấp trước lúc khóa dùng lại được, vì token không tra DB phiên (cùng gốc với giới hạn của QĐ-12); refresh token đã thu hồi nên vẫn chết. Nếu cần chặn hẳn (khóa vì nghi tài khoản bị chiếm) thì phải thêm mốc "token hợp lệ từ" vào `khach_hang`/`nhan_vien` qua `/doi-schema` (ghi ở "Việc phát sinh").
  - **`ly_do` khóa do Admin tự nhập và không được kiểm tra nội dung** (rà soát T1.5, L3): nhật ký chỉ che theo tên khóa nên một chuỗi tự do có thể chứa số điện thoại hay thông tin sức khỏe nếu Admin gõ vào. Giao diện nhắc không nhập thông tin cá nhân; chưa chuyển sang danh sách mã lý do.
  - **Mở khóa gỡ cả khóa tạm** do đoán mật khẩu và xóa bộ đếm sai; khách đặt lại mật khẩu bằng OTP vẫn không tự mở được khóa của Admin (QĐ-11).
  - **Thao tác ghi của AD02 cũng đòi người thực hiện là ADMIN** (`dam_bao_la_admin`, như QĐ-13): `customer.manage` là một trong 18 quyền chỉ ADMIN giữ.
  - **Khách đã xóa (ẩn danh hóa, [DB23]) không hiện và không thao tác được** (404).
  - **Tìm số điện thoại:** chuỗi giống số điện thoại được đưa về dạng lưu (`+84`, `84`, khoảng trắng, gạch) để Admin gõ theo thói quen nào cũng tìm ra; một phần số cũng khớp. Escape LIKE dùng chung `core/tim_kiem.mau_tim_like` với AD01.
  - **Nhãn trạng thái dùng chung** `lib/trangThai.ts` + `NhanTrangThai` (spec 09 mục 3, 4): test đối chiếu từng giá trị enum với `schema.d.ts` sinh từ OpenAPI nên thêm trạng thái ở backend mà quên nhãn thì test báo.
  - **Liên kết trong khu quản trị phải giữ tiền tố `/quan-tri`:** trang AD02 từng viết `to="/khach-hang/1"` nên bấm vào bị đưa ra khu cửa hàng; test đơn vị chạy ở gốc `/` không thấy, chỉ lộ khi chạy trên trình duyệt. Từ nay test trang con của khu phải có ca chạy dưới tiền tố.
- **Hệ quả:** spec 06 mục 3.6; spec 09 mục 2.3; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

## QĐ-15: Cấu hình hệ thống và nhật ký (2026-10-16, task T1.6)
- **Quyết định:**
  - **AD08 quản lý 15 khóa, bốn khóa `ai_*` thuộc AD09** (`ai.config`, T6.x): AD08 không liệt kê và không sửa được chúng (`PUT` là 404), để hai chức năng có hai mã quyền khác nhau không giẫm lên nhau.
  - **Mỗi khóa có kiểu và khoảng giá trị** (bảng ở spec 02 mục 6, code ở `core/cau_hinh_khoa.py`; test đối chiếu từng con số giữa hai nơi và với mọi giá trị mặc định của seed). Lý do: `dang_nhap`, `otp`, hạn thanh toán... đọc thẳng giá trị rồi `int(...)`, nên giá trị sai (âm, 0, chuỗi) làm đăng nhập hay đặt hàng lỗi hàng loạt. Chọn khoảng chặt có chủ ý: `so_lan_dang_nhap_sai_toi_da` tối thiểu 3 (đặt 1 thì ai cũng khóa tạm được tài khoản người khác bằng một lần thử sai), giới hạn OTP tối đa 20 lần mỗi số mỗi giờ (mỗi tin SMS tốn tiền). Số phải là số nguyên thật: không nhận `5.0`, `"5"`, `true`. Muốn nới khoảng thì sửa bảng ở spec 02 rồi mới sửa code.
  - **Khóa lạc quan `phien_ban`** (cùng cơ chế với AD18, QĐ-13): dấu vân tay nội dung 16 ký tự hex của giá trị hiện tại; lưu lệch là `409 DU_LIEU_DA_THAY_DOI`. Giao diện tải lại bản mới nhưng GIỮ giá trị người dùng đang gõ và báo giá trị hiện tại trên máy chủ để họ tự quyết định, không bao giờ ghi đè ngầm.
  - **Khóa chưa có trong bảng** (chưa seed) vẫn được liệt kê với `gia_tri = null` và tạo được bằng `PUT` (nhật ký ghi `tao`); hai Admin tạo cùng lúc thì bên thua nhận 409 nhờ savepoint.
  - **Có hiệu lực ngay:** mọi nơi dùng đọc `cau_hinh` mỗi lần, không có bộ nhớ đệm nên không phải xóa gì. Thao tác ghi cũng đòi người thực hiện là ADMIN (`dam_bao_la_admin`, QĐ-13).
  - **Nhật ký không bao giờ cho Admin thấy dữ liệu sức khỏe** (CLAUDE.md quy tắc 7): với `ho_so_suc_khoe`, `di_ung` giá trị bị BỎ ngay lúc ghi (`ghi_nhat_ky`) và che lại lúc ĐỌC (AD15) phòng dòng cũ ghi trước khi có quy tắc; các khóa nhạy cảm còn lại che theo tên khóa ở cả hai chiều, danh sách thêm `dang_mang_thai`, `dang_cho_con_bu`, `nam_sinh`, `thong_tin_nhan_hoan`. Việc này xử lý mục "Việc phát sinh" T1.3-rv.
  - **Nhật ký chỉ đọc và chỉ hiển thị người thực hiện** bằng id, mã và tên (không email, số điện thoại). Khoảng ngày tính theo giờ Việt Nam và gồm cả hai đầu; bộ lọc kết hợp bằng AND; chuỗi lọc chặn byte NUL từ đầu (PostgreSQL báo 500 với NUL).
  - **Giao diện:** `InputNumber` của antd không được đặt `min`/`max` vì nó âm thầm ép giá trị về khoảng, người dùng gõ 99 mà thấy 20 và không biết mình nhập sai; thay vào đó báo lỗi ngay và tắt nút Lưu. Ô giờ dùng `<input type="time">`, hiển thị theo ngôn ngữ trình duyệt.
- **Hệ quả:** spec 02 mục 6; spec 06 mục 3.7, 3.8; spec 09 mục 2.3; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.


## QĐ-16: Danh mục và dữ liệu dùng chung (2026-10-16, task T2.1)
- **Quyết định:**
  - **"Ẩn" và "xóa mềm" là hai trạng thái khác nhau** (lộ trình ghi "ẩn = xóa mềm", mơ hồ; cần người xác nhận). `dang_hien_thi = false` là ẨN: đảo ngược được bằng một cú bấm, danh mục và cả cây con biến khỏi cửa hàng (áp dụng ở danh sách công khai T2.4) nhưng vẫn nằm trong cây của Admin và vẫn gắn sản phẩm. `deleted_at` là XÓA MỀM (`DELETE`): danh mục rời cây của Admin, `slug` vẫn được giữ chỗ. Cách hiểu này giữ được điều lộ trình cần ("bỏ khỏi cửa hàng mà không mất dữ liệu") mà vẫn cho Admin tạm ẩn một nhánh rồi hiện lại.
  - **Xóa danh mục bị từ chối khi còn sản phẩm chưa xóa** (`409 DANH_MUC_CON_SAN_PHAM`, đúng lộ trình) **hoặc còn danh mục con chưa xóa** (`409 DANH_MUC_CON_DANH_MUC`, mã mới): xóa từ lá lên; muốn bỏ cả nhánh khỏi cửa hàng thì dùng Ẩn. Sản phẩm đã xóa mềm không chặn xóa danh mục.
  - **Mọi thao tác ghi vào cây** (tạo, chuyển, xóa) lấy khóa tư vấn `pg_advisory_xact_lock(hashtext('nha_thuoc.danh_muc_cay'))` rồi đọc cả cây: kiểm tra giới hạn 3 cấp và chống vòng chỉ đúng khi thấy một cây nhất quán (hai Admin cùng chuyển A vào B và B vào A sẽ tạo vòng nếu không tuần tự hóa; đã tái hiện bằng test đồng thời). Chuyển danh mục tính cả chiều cao cây con mang theo: nhánh cao 2 không đặt được dưới danh mục cấp 2.
  - **Xóa danh mục khóa dòng `FOR UPDATE` TRƯỚC khi đếm sản phẩm.** Tạo/đổi danh mục của sản phẩm giữ khóa khóa-ngoại `KEY SHARE` trên dòng danh mục nên hai bên không lọt khe: giao dịch xóa chờ giao dịch thêm sản phẩm rồi thấy sản phẩm đó. **Việc cho T2.2:** khi gán danh mục cho sản phẩm phải `SELECT ... FROM danh_muc WHERE id = ? AND deleted_at IS NULL FOR SHARE` rồi mới ghi, để không gắn sản phẩm vào danh mục vừa bị xóa mềm.
  - **Đổi tên không đổi `slug`** (đường dẫn công khai ổn định, không gãy liên kết và SEO); `slug` duy nhất trên cả dòng đã xóa mềm (thêm hậu tố `-2`, `-3`). Tên danh mục không trùng giữa các danh mục cùng cha, so sánh không phân biệt hoa thường và dấu (`f_unaccent(lower())`); tên phải tạo ra được một `slug` (có ít nhất một chữ hoặc số).
  - **Sắp xếp và chuyển cha dùng một thao tác `PUT /noi-bo/danh-muc/{id}/vi-tri`** (cha mới hoặc gốc + chỉ số) thay vì `PATCH thu_tu`: kéo thả là một ý định nên phải nguyên tử; chỉ số lớn quá thì đặt cuối, `thu_tu` của cha cũ và cha mới được đánh lại liên tục từ 0; đúng chỗ cũ thì không ghi gì.
  - **AD05: thương hiệu và nhà sản xuất xóa cứng dựa vào khóa ngoại; HOẠT CHẤT KHÔNG CÓ XÓA** (sửa sau rà soát T2.1; bản đầu cho xóa và chấp nhận một "bit tổng hợp"). Thương hiệu, nhà sản xuất còn sản phẩm gắn vào (kể cả đã xóa mềm) thì DB từ chối trong một savepoint và API trả `409 DU_LIEU_DANG_DUOC_SU_DUNG`; không đếm trước rồi xóa vì có khe hở với giao dịch đang thêm tham chiếu. Hoạt chất không có route `DELETE` (mọi vai trò nhận `405`): một hoạt chất có thể nằm trong dị ứng của khách mà Admin không được thấy (CLAUDE.md quy tắc 7), nên kết quả `204` hay `409` của một lần xóa cho biết có khách dị ứng hoạt chất đó, và vì tạo hoạt chất mồi rồi thử xóa là xong nên dò được từng hoạt chất (đã chạy thử), kể cả bởi vai trò khác nếu `master_data.manage` được ủy quyền. Nhập nhầm thì sửa tên; muốn gỡ hẳn cần cờ "ngừng dùng" qua `/doi-schema` (ghi ở "Việc phát sinh"). Danh sách hoạt chất không có số liệu về dị ứng.
  - **Trùng dữ liệu của AD05:** thương hiệu và hoạt chất theo tên, nhà sản xuất theo cặp (tên, quốc gia) với quốc gia trống được coi là một giá trị, đều không phân biệt hoa thường và dấu. Ràng buộc unique của DB chỉ bắt trùng từng ký tự (và bỏ qua `quoc_gia` NULL), nên service kiểm tra và tuần tự hóa tạo/đổi tên bằng khóa tư vấn riêng của từng nhóm (`nha_thuoc.<bảng>.ten`).
  - **`master_data.manage` không thuộc nhóm chỉ-ADMIN** (dược sĩ giữ `chi_xem`), nên thao tác ghi AD05 không có chốt `dam_bao_la_admin` như AD01/AD02/AD03: nếu Admin ủy quyền mức đầy đủ cho vai trò khác qua AD18 thì vai trò đó ghi được. `category.manage` thì chỉ-ADMIN nên AD03 có chốt.
  - **Đường dẫn ảnh/logo** chỉ nhận `/...` hoặc `http(s)://...` (không `//host`, `/\host`, `javascript:`, `data:`, khoảng trắng), tối đa 500 ký tự. Mọi chuỗi nhập bị từ chối nếu chứa ký tự điều khiển (NUL làm PostgreSQL báo 500), ký tự định dạng vô hình (U+200B, BOM, bidi: qua mặt kiểm tra trùng tên) hoặc surrogate đơn lẻ (JSON `"\ud800"` làm asyncpg báo 500); trống thành `null`. Kiểm tra phía giao diện (`lib/duLieuChung.ts`) dùng chung bảng ca với backend.
  - **Sắp xếp lại làm đổi `updated_at` của các anh em bị đánh lại `thu_tu`** và nhật ký ghi danh sách id đó (`anh_em_doi_thu_tu`), để dấu vết thay đổi không chỉ có một dòng cho danh mục được kéo.
  - **`so_san_pham`:** danh mục đếm sản phẩm chưa xóa nằm TRỰC TIẾP trong danh mục; thương hiệu và nhà sản xuất đếm cả sản phẩm đã xóa mềm (khóa ngoại vẫn tham chiếu, và đó là điều quyết định xóa được hay không); hoạt chất đếm số dòng `thanh_phan`.
- **Hệ quả:** spec 06 mục 3.9, 3.10 và bảng mã lỗi (hai mã mới); spec 09 mục 2.3; `core/phan_trang.lay_trang(nhieu_cot=True)` cho truy vấn kèm cột đếm; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.


## QĐ-17: Sản phẩm (thông tin thương mại) và lưu trữ tệp công khai (2026-10-16, task T2.2)
- **Quyết định:**
  - **AD04 chỉ có thông tin thương mại; nội dung chuyên môn (chỉ định, liều dùng...) thuộc DS10 (T2.3).** Mọi body của AD04 từ chối trường lạ (`400`), nên Admin không sửa được nội dung chuyên môn qua đây dù biết tên trường. Endpoint chuyên môn dành cho dược sĩ làm ở T2.3. Đọc cần `product.commercial.manage` mức `xem`; ghi cần `day_du` và người thực hiện là ADMIN (`dam_bao_la_admin`, như QĐ-13), vì quyền này chỉ cấp cho ADMIN.
  - **Khóa lạc quan `phien_ban` cho cả sản phẩm** (cùng cơ chế QĐ-13, QĐ-15): dấu vân tay nội dung của sản phẩm gồm đơn vị, thành phần, ảnh và các tên hiển thị kèm theo (danh mục, thương hiệu, nhà sản xuất, hoạt chất). Mọi thao tác ghi đòi `phien_ban`, khóa dòng sản phẩm `FOR UPDATE` trước khi so, lệch là `409 DU_LIEU_DA_THAY_DOI`. Bốn route con (đơn vị, thành phần, ảnh) cũng dùng chung một `phien_ban` của cả sản phẩm: lưu đơn vị làm `phien_ban` của form thông tin cũ đi, nên giao diện lấy lại bản trả về sau mỗi lần ghi và KHÔNG tự làm mới chi tiết khi focus lại cửa sổ (nếu làm mới ngầm thì bản sửa dở được lưu đè lên thay đổi của người khác mà không báo). Form thông tin chỉ gửi những trường người dùng đã đổi, nên lần lưu sau xung đột không ghi đè trường người kia vừa sửa. Hai tab thay CẢ danh sách (đơn vị, thành phần) thì KHÔNG giữ chữ đang gõ sau 409: bản đang gõ là một danh sách đầy đủ, lưu lại với `phien_ban` mới sẽ xóa im lặng đơn vị/thành phần người kia vừa thêm (rà soát T2.2 đã tái hiện), nên form được thay bằng danh sách mới của máy chủ kèm thông báo chỉnh sửa chưa lưu đã bị bỏ.
  - **SKU** tự chuyển chữ hoa, trùng so không phân biệt hoa thường và kể cả sản phẩm đã xóa mềm (so ở phía DB bằng `upper(sku)`, vì dòng nhập ngoài API có thể mang chữ thường). **`slug`** sinh một lần từ tên, thêm `-2`, `-3` nếu trùng với bất kỳ sản phẩm nào kể cả đã xóa, và KHÔNG đổi khi đổi tên (đường dẫn công khai ổn định, như danh mục ở QĐ-16).
  - **Định danh và mã vạch tuần tự hóa bằng khóa tư vấn** (`nha_thuoc.san_pham.dinh_danh`, `nha_thuoc.san_pham.ma_vach`): DB không có unique cho mã vạch (chỉ index thường) và unique của SKU chỉ bắt trùng từng ký tự. Mã vạch không trùng với đơn vị của bất kỳ sản phẩm CHƯA XÓA nào khác (so không phân biệt hoa thường) để quét mã ở quầy ra đúng một dòng; sản phẩm đã xóa mềm không giữ chỗ (xóa là cuối cùng, không có khôi phục, mà mã vạch in trên hộp thuốc nên Admin xóa nhầm vẫn phải tạo lại được); hai PUT song song đặt cùng mã vạch cho hai sản phẩm khác nhau thì một bên nhận `409 TRUNG_DU_LIEU` (đã có test đồng thời).
  - **Thuốc kê đơn không đặt nổi bật** (`400`; không quảng bá thuốc kê đơn trên trang chủ, CLAUDE.md quy tắc 6): chặn ở service chứ không chỉ ở giao diện, và đổi loại sang kê đơn khi đang nổi bật phải bỏ nổi bật trong cùng yêu cầu (giao diện tự làm việc đó).
  - **Đơn vị quy đổi thay cả danh sách trong một giao dịch**, áp theo pha để không va ràng buộc: xóa đơn vị bỏ đi (trong savepoint; khóa ngoại từ chối thì `409 DU_LIEU_DANG_DUOC_SU_DUNG`), đưa tên về tên tạm và gỡ cờ mặc định, rồi áp giá trị cuối theo thứ tự "rời hệ số 1 trước, vào hệ số 1 sau" (partial unique một đơn vị cơ sở), thêm đơn vị mới. Đơn vị đang được tham chiếu (giỏ hàng, đơn hàng, phiếu nhập) không xóa và không đổi `he_so` được; sản phẩm đã có lô không đổi `he_so` của đơn vị nào và không thay đơn vị cơ sở (số lượng tồn tính theo đơn vị cơ sở nên đổi là đổi nghĩa mọi con số đã ghi). Đổi tên, giá, mã vạch, bán online, mặc định và thêm đơn vị mới thì luôn được. `san_pham.don_vi_co_so` không nhận từ client mà suy ra từ đơn vị `he_so = 1`. Không có gì đổi thật thì không ghi nhật ký và giữ nguyên `updated_at`.
  - **Xóa sản phẩm là xóa mềm** và bị từ chối bằng `409 SAN_PHAM_CON_TON_KHO` (mã mới) khi còn lô có tồn, đang giữ hoặc biệt trữ lớn hơn 0 (đưa về 0 qua nghiệp vụ kho trước); muốn ngừng bán mà giữ lịch sử thì đặt `trang_thai = ngung_kinh_doanh`. Việc xét tồn khóa mọi lô của sản phẩm `FOR UPDATE` (id tăng dần) TRƯỚC khi đếm, và mọi hàm TĂNG tồn trong `ton_kho.py` gọi `kiem_tra_san_pham_chua_xoa` sau khi khóa lô: nhập kho khóa lô trước thì xóa chờ rồi thấy tồn > 0 và bị từ chối; xóa khóa trước thì nhập kho chờ rồi đọc được `deleted_at` và bị từ chối (`404 KHONG_TIM_THAY`). Không có đường thứ ba để tồn mắc kẹt dưới sản phẩm đã xóa (rà soát T2.2 đã tái hiện lỗi khi chỉ đếm không khóa; tạo lô mới thì khóa khóa-ngoại của INSERT trên dòng sản phẩm chờ xóa).
  - **Gán danh mục khóa dòng danh mục `FOR SHARE`** (việc đã ghi ở QĐ-16): tạo sản phẩm và đổi danh mục không gắn vào danh mục vừa bị xóa mềm; đã tái hiện đua nhau ở cả hai chiều bằng test đồng thời.
  - **Lưu trữ tệp công khai** (spec 08 mục 6): `LUU_TRU_THU_MUC/cong_khai/<thư mục>/<uuid>.<đuôi>`; kiểu tệp nhận dạng bằng magic bytes (jpeg, png, webp; không tin tên file hay `Content-Type`), tối đa 5 MB (`413 TEP_QUA_LON`, mã mới), tối đa 20 ảnh mỗi sản phẩm. Phục vụ qua `GET /api/v1/tep/<khóa>` công khai (khóa chỉ gồm chữ thường, số, gạch ngang và `/`; khóa sai là `404`, không có đường thoát khỏi thư mục), kèm `X-Content-Type-Options: nosniff` và `Cache-Control: public, max-age=31536000, immutable` (tên là UUID nên không bao giờ đổi nội dung). **Không có endpoint upload chung:** ảnh đi kèm bản ghi của sản phẩm nên dùng quyền `product.commercial.manage`; banner và bài viết (T7.x) làm endpoint riêng cùng khuôn với `cms.manage`. Tệp ghi ra đĩa trước khi giao dịch commit nên bị dọn nếu giao dịch hủy (hook `after_soft_rollback`), và tệp của ảnh bị xóa chỉ bị xóa SAU commit (hook `after_commit`): commit hỏng thì ảnh trong DB vẫn có tệp.
  - **Mỗi thao tác ảnh trả về cả sản phẩm** (`SanPhamChiTiet`) để giao diện lấy ngay `phien_ban` mới. Ảnh đầu tiên tự là ảnh chính; xóa ảnh chính thì ảnh đầu danh sách thành chính; đổi thứ tự phải gửi đúng tập id hiện có (hoán vị), đặt ảnh chính gỡ cờ ở ảnh cũ trước (partial unique đúng một ảnh chính).
  - **Giao diện:** thương hiệu, nhà sản xuất, hoạt chất chọn bằng ô tìm phía máy chủ (danh sách có thể dài hàng nghìn dòng), nên `GET /noi-bo/san-pham/{id}` trả kèm `ten_thuong_hieu`, `ten_nha_san_xuat` (như `ten_hoat_chat` của thành phần) để ô chọn hiện nhãn mà không phải tải thêm. Thêm sản phẩm là một form gửi một lần (thông tin, đơn vị, thành phần) để không có sản phẩm dở dang; ảnh tải lên được sau khi tạo. Thân tải ảnh bị giới hạn ở middleware ngay từ `Content-Length` (hoặc khi đếm đủ byte của thân gửi theo mảnh), trước xác thực: Starlette đọc cả multipart vào tệp tạm trước khi chạy dependency nên không có lớp này thì request chưa đăng nhập vẫn ghi được tệp lớn vào đĩa; test duyệt OpenAPI báo đỏ nếu một route multipart mới thiếu quy tắc. Schema ĐỌC dùng `TienDoc` (chỉ định dạng xuất), không dùng `Tien` (bộ kiểm đầu vào): một dòng NUMERIC(14,2) có phần lẻ nhập ngoài API không được làm cả trang chi tiết và danh sách 500. Tên đơn vị tạm trong lúc thay danh sách chứa ký tự điều khiển (`DonViVao` từ chối), không thể trùng tên Admin nhập. Kiểm tra chống symlink so với VÙNG CÔNG KHAI (`cong_khai/`) chứ không chỉ thư mục lưu trữ (vùng riêng tư nằm cạnh). Tải ảnh gửi `multipart/form-data` (`bodySerializer` tạo `FormData`, trình duyệt tự đặt `Content-Type` kèm boundary); kiểm tra loại và dung lượng phía giao diện chỉ để báo sớm.
- **Hệ quả:** spec 06 mục 3.11, 4 (hai mã lỗi mới `SAN_PHAM_CON_TON_KHO`, `TEP_QUA_LON`), 7; spec 08 mục 6; spec 09 mục 2.3; `core/luu_tru.py`, biến môi trường `LUU_TRU_THU_MUC`, phụ thuộc `python-multipart`; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.


## QĐ-18: Nội dung chuyên môn, tương tác hoạt chất và cảnh báo (2026-10-16, task T2.3)
- **Quyết định:**
  - **Mỗi lần sửa là một phiên bản mới, không sửa tại chỗ** (đúng lộ trình): `phien_ban` tăng dần theo sản phẩm, trạng thái `nhap`; lịch sử đầy đủ để so sánh. Trường bỏ trống là `null`, KHÔNG kế thừa từ bản trước (giao diện điền sẵn từ bản mới nhất): kế thừa ngầm làm "xóa một trường" không biểu diễn được. Body bắt buộc có `phien_ban_co_so` (phiên bản mới nhất người soạn đã thấy, có thể `null`), lệch là `409`: hai dược sĩ soạn cùng lúc không ngầm bỏ qua bản của nhau. Nội dung giống hệt bản mới nhất là `400` (không sinh bản trùng khi bấm đúp).
  - **Mỗi sản phẩm tối đa MỘT bản `da_duyet` = bản hiển thị; duyệt bản mới đưa bản cũ sang `luu_tru`**: lộ trình ghi "phiên bản hiển thị = bản đã duyệt mới nhất", nên luôn chỉ có một ứng viên và truy vấn của khách, AI (`noi_dung_da_duyet`) không phải sắp xếp hay so ngày. **Không duyệt lùi**: bản nháp CŨ hơn bản đang hiển thị không duyệt được (`409`), vì duyệt nó sẽ âm thầm đưa nội dung hiển thị về một bản cũ mà không ai quyết định; muốn dùng lại nội dung cũ thì soạn bản mới từ nó. Bản nháp bỏ được (`luu_tru`); bản đã duyệt thì không (gỡ nội dung đang hiển thị khỏi cửa hàng là việc khác, chưa có yêu cầu). Mọi thao tác ghi khóa dòng sản phẩm `FOR UPDATE` trước (cùng thứ tự ở mọi hàm) nên đánh số và duyệt không đua nhau (đã có test đồng thời).
  - **Người soạn có thể tự duyệt bản của mình** (CẦN NGƯỜI XÁC NHẬN): spec 03 mục 7 chỉ bắt tách nhiệm vụ cho phiếu kho và hoàn tiền, không nhắc nội dung chuyên môn; nhà thuốc quy mô một dược sĩ mà bắt người duyệt khác người soạn thì không đăng được gì. Nhật ký vẫn ghi người soạn (`nguoi_soan_id`) và người duyệt (`duoc_si_duyet_id`). Nếu cần kiểm tra chéo, thêm một điều kiện vào `noi_dung.duyet` và một dòng ở spec 03 mục 7.
  - **Chỉ dược sĩ ghi, ở hai lớp:** `content.professional.edit`/`content.approve` ở mức đầy đủ và `dam_bao_la_duoc_si` (người thực hiện có vai trò PHARMACIST) ở đầu mọi hàm GHI. Lớp thứ hai cần vì Admin gán được hai quyền này cho vai trò khác qua AD18; không có nó thì "Admin không sửa nội dung chuyên môn" (spec 03 mục 7) bị lách bằng một tài khoản kho. Admin có `chi_xem` nên đọc được (AD16, giao diện xem ở T6.7).
  - **Tương tác hoạt chất:** cặp lưu theo thứ tự id tăng dần, client gửi thứ tự nào cũng được; thêm trùng cặp là `409 TRUNG_DU_LIEU` kể cả khi hai dược sĩ thêm cùng lúc (savepoint, không 500); sửa và xóa dùng `phien_ban` dấu vân tay (khóa lạc quan như QĐ-13); xóa cứng (không có dữ liệu khác tham chiếu cặp). `kiem_tra_tuong_tac` chỉ báo cặp có hai hoạt chất nằm ở hai sản phẩm KHÁC nhau của danh sách: thuốc phối hợp mà nhà sản xuất đã bào chế sẵn hai hoạt chất thì không phải một "tương tác khi dùng chung" để cảnh báo người mua; hai sản phẩm cùng chứa một hoạt chất (trùng hoạt chất) cũng không phải tương tác (việc đó thuộc DS04/DS08 khi cần).
  - **Cảnh báo dị ứng** (`kiem_tra_di_ung`): dị ứng với một hoạt chất được coi là `chong_chi_dinh` (bảng `di_ung` không có mức độ riêng). Hàm đọc `di_ung` bên trong service nhưng chỉ trả "sản phẩm nào, hoạt chất nào": không trả `ghi_chu` (văn bản tự do có thể chứa chi tiết bệnh), không trả danh sách dị ứng, không ghi log (CLAUDE.md quy tắc 7, spec 03 mục 5.1). Hàm không kiểm `dong_y_su_dung`: cảnh báo chỉ quay về chính khách (giỏ hàng) hoặc dược sĩ đang xử lý yêu cầu của khách đó (qua `duoc_doc_ho_so_suc_khoe` ở T5.x), nên người gọi quyết định ai thấy; hàm không thay cổng đọc hồ sơ.
  - **Duyệt bài viết sức khỏe chỉ làm phần dược sĩ:** `GET/POST /noi-bo/bai-viet-cho-duyet` (danh sách `nhap`, chi tiết, duyệt) với `content.approve`; bài `chinh_sach` và `faq` không qua dược sĩ. Soạn, sửa, đăng bài và giao diện duyệt nối vào ở T2.6 (AD07), theo đúng ghi chú của lộ trình ("khi T2.6 xong thì nối vào").
  - **Giao diện:** `/nhan-vien/noi-dung-chuyen-mon` (danh sách sản phẩm theo tình trạng, soạn phiên bản mới điền sẵn từ bản mới nhất, so sánh hai phiên bản từng trường, duyệt, lưu trữ nháp) và `/nhan-vien/tuong-tac` (bảng, thêm, sửa, xóa). Mọi nút ghi bọc `YeuCauQuyen`; nút Duyệt cần `content.approve`.
  - **Dữ liệu mẫu:** nội dung chuyên môn và tương tác mẫu cho các sản phẩm của `seed --mau` thêm ở T2.4, nơi khách bắt đầu đọc chúng (để có dữ liệu thật mà kiểm giao diện chi tiết sản phẩm).
- **Hệ quả:** spec 03 mục 7; spec 06 mục 3.12; spec 09 mục 2.2; `core/phan_quyen.dam_bao_la_duoc_si`; `modules/chuyen_mon/`; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

## QĐ-19: Cửa hàng công khai: trang chủ, danh mục, sản phẩm (2026-10-16, task T2.4)
- **Quyết định:**
  - **"Hiển thị với khách"** = sản phẩm chưa xóa, `dang_kinh_doanh`, và danh mục của nó cùng MỌI tổ tiên chưa xóa và `dang_hien_thi` (QĐ-16). Áp cho mọi danh sách, bộ lọc, trang chủ, sản phẩm tương tự VÀ chi tiết sản phẩm (404 khi nằm trong nhánh ẩn). Cây danh mục được nạp một lần rồi tính nhánh hiển thị trong bộ nhớ thay vì CTE đệ quy ở mỗi truy vấn (cây nhỏ, tối đa 3 cấp).
  - **Giá của thẻ sản phẩm** là giá đơn vị BÁN ONLINE mặc định, không có thì đơn vị online có `he_so` nhỏ nhất, không có đơn vị online thì `null` ("Chỉ bán tại nhà thuốc"). Lọc và sắp xếp theo giá dùng đúng giá này. **Còn hàng** = tồn khả dụng > 0 trên các lô `dang_ban` còn hạn (`HSD > hôm nay theo giờ VN`, kể cả khi nhãn lô chưa được job HT01 cập nhật); ở chi tiết, mỗi đơn vị còn hàng khi tồn khả dụng >= `he_so` của nó. API không lộ số lượng tồn.
  - **Thuốc kê đơn có mặt ở danh sách và chi tiết** (kèm `can_tu_van`, khách xem được thông tin và giá tham khảo) nhưng KHÔNG ở khu quảng bá: "nổi bật", "bán chạy" của trang chủ và "sản phẩm tương tự" loại thuốc kê đơn ngay ở truy vấn, không dựa vào cờ `la_noi_bat` (DB không cấm kê đơn nổi bật, chỉ service AD04 cấm). Trang chi tiết kê đơn không có nút thêm vào giỏ.
  - **Bán chạy** = số dòng `ct_don_hang` của đơn không `da_huy` trong 30 ngày qua (đúng lộ trình "đếm `ct_don_hang` 30 ngày"; đếm dòng chứ không cộng số lượng vì các dòng khác đơn vị không cộng được). Khu "Bán chạy" của trang chủ chỉ có sản phẩm có ít nhất một dòng: chưa có đơn nào thì khu ẩn (seed mẫu không tạo đơn vì đơn chỉ được tạo qua `chuyen_trang_thai`, T4.x).
  - **Nội dung chuyên môn ở chi tiết** chỉ đọc từ `noi_dung_da_duyet` (cửa duy nhất) và KHÔNG kèm tên người soạn hay duyệt; sản phẩm đã xóa mềm trả `None` ngay trong hàm đó (rà soát T2.3).
  - **Đánh giá** chỉ tính `dang_hien`; tên người đánh giá rút gọn ("Nguyễn A."); API trả `tong_sao` và `phan_bo` để trình duyệt tính điểm trung bình (không trả số thực). Hỏi đáp (KTV15) chưa có ở T2.4; đánh giá do T5.x/DS11 tạo và kiểm duyệt.
  - **Lịch sử xem** ghi ở máy chủ khi gọi chi tiết: khách đăng nhập theo `khach_hang_id` từ token (bỏ qua mã phiên client gửi), vãng lai theo header `X-Ma-Phien` (mẫu `[A-Za-z0-9_-]{8,64}`, sai thì bỏ qua), không có cả hai thì không ghi; cùng người xem lại cùng sản phẩm trong 30 phút chỉ giữ một dòng. Trang chi tiết đợi `daKhoiPhuc` để không ghi khách đã đăng nhập thành vãng lai.
  - **Bộ lọc** của trang danh mục lấy từ `GET /bo-loc-san-pham` (thương hiệu và đối tượng thật của sản phẩm hiển thị, khoảng giá), vì `doi_tuong_su_dung` là chữ tự do. Route này KHÔNG nằm dưới `/san-pham/...` để không bị slug sản phẩm trùng tên che.
  - **Banner** chỉ đọc (`GET /banner`, `GET /trang-chu`); CRUD banner là việc của T7.x. Seed mẫu thêm 4 banner trỏ ảnh SVG trong `frontend/public/banner/` và nội dung chuyên môn đã duyệt cho 7 sản phẩm (gồm một thuốc kê đơn).
  - **`con_hang` của thẻ không xét đơn vị bán online:** sản phẩm chỉ bán tại quầy mà còn tồn vẫn có `con_hang = true` (thẻ ghi "Chỉ bán tại nhà thuốc"), và bộ lọc "Chỉ còn hàng" vẫn trả nó. Chấp nhận vì tình trạng kho là sự thật về hàng, còn việc mua online do `chi_ban_tai_quay`/`gia = null` thể hiện.
  - **Ghi lịch sử xem có giới hạn theo IP** (120 lượt/10 phút, bộ đếm trong bộ nhớ như OTP): mã phiên do client chọn nên không có giới hạn thì một script quay mã làm phình `lich_su_xem` và lệch gợi ý AI07.
  - **Chưa có giỏ hàng:** nút "Thêm vào giỏ" của sản phẩm thường hiện nhưng bị khóa (Tooltip "Giỏ hàng đang được xây dựng"); T4.1 nối vào `KhuMuaHang` trong `TrangChiTietSanPham.tsx`.
- **Hệ quả:** spec 06 mục 3.13; spec 09 mục 2 (mô tả trang cửa hàng); `modules/cua_hang/`; `frontend/src/khu/cua-hang/`, `lib/lienKet.ts`, `lib/maPhien.ts`; `seed --mau`; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

## QĐ-20: Tìm kiếm từ khóa (2026-10-16, task T2.5)
- **Quyết định:**
  - **Khớp** bằng `word_similarity` trên tên sản phẩm, tên hoạt chất và `ten_khac` (qua `thanh_phan`), đúng biểu thức `f_unaccent(lower(...))` của các index GIN (kiểm bằng `EXPLAIN ANALYZE` trên 20.000 sản phẩm với cấu hình mặc định: `Bitmap Index Scan on san_pham_ten_trgm`, 2,6 ms; điều kiện gộp bằng UNION vì `OR` giữa điều kiện có index và `IN (subquery)` làm PostgreSQL quét tuần tự cả bảng, đo 155 ms chỉ riêng câu đếm). Hoạt chất khớp thì mọi sản phẩm hiển thị chứa nó khớp theo. Từ khóa nhiều từ: khớp nếu cả cụm khớp tên, HOẶC mỗi từ (tối đa 6) khớp tên (gần đúng hoặc chứa), nên "para 5", "vit c" (từ cuối đang gõ dở) vẫn ra kết quả; chấp nhận giới hạn: thêm một từ không có trong tên ("paracetamol 500mg stada") thì không khớp, và `word_similarity` có thể khớp cả từ gần giống ("tho" với "thuốc ho"). Chưa tìm trong nội dung chuyên môn hay `chi_dinh` (triệu chứng, công dụng): đó là phần ngữ nghĩa của T7.2.
  - **Xếp hạng** = độ khớp làm tròn 0,1 (để chênh lệch nhỏ như 0,83 và 0,87 không lấn át "còn hàng" và "bán chạy"), rồi còn hàng, rồi bán chạy, rồi độ khớp thô, rồi `id`. Thuốc kê đơn có mặt, kèm "Cần tư vấn" (KVL04, spec 07 mục 271); không có khu quảng bá nên không cần loại.
  - **Từ khóa dưới 2 ký tự** trả rỗng (không phải 400) để ô gõ tìm kiếm không hiện lỗi giữa chừng; không ghi lịch sử.
  - **Lịch sử tìm kiếm** ghi cả khi không có người (không `khach_hang_id`, không `ma_phien`) để thống kê từ khóa không kết quả (index `lich_su_tim_kiem_rong`); chỉ trang 1; dedupe 30 phút; giới hạn ghi theo IP như lịch sử xem (QĐ-19). Từ khóa là chuỗi người dùng gõ: không phải dữ liệu sức khỏe của hồ sơ nhưng có thể gợi ý bệnh; chỉ nằm trong bảng này, không đưa vào log ứng dụng hay nhật ký hệ thống.
  - **Gợi ý** = tối đa 6 sản phẩm + 2 hoạt chất (có sản phẩm hiển thị); không ghi lịch sử; không dùng khóa cache vì rẻ (~30 ms), nhưng giới hạn 240 lượt/phút/IP (`429 QUA_GIOI_HAN`; giao diện bỏ qua lỗi gợi ý) vì là route công khai và mỗi lượt là một truy vấn tìm kiếm.
  - **Xếp hạng theo nhóm làm tròn 0,1** có ranh giới cứng (0,849 và 0,851 khác nhóm): hệ quả của thiết kế, chấp nhận.
- **Hệ quả:** spec 06 mục 3.13, 09; `modules/cua_hang/tim_kiem.py`; `frontend/src/khu/cua-hang/{OTimKiem,TrangTimKiem,timKiem}`; `backend/CLAUDE.md`.

## QĐ-21: Nội dung website: banner, bài viết, chính sách, FAQ (2026-10-16, task T2.6)
- **Quyết định:**
  - **Chỉ Admin soạn và đăng** (mã `cms.manage` chỉ ADMIN giữ, thêm `dam_bao_la_admin` ở service như AD03/AD04); dược sĩ chỉ duyệt bài sức khỏe qua `content.approve` (T2.3). Admin soạn xong không tự duyệt được.
  - **Sửa bài đã duyệt đưa về chờ duyệt** (chỉ với bài sức khỏe, và chỉ khi đổi tiêu đề, nội dung hay ảnh bìa): bản dược sĩ từng duyệt không còn là bản đang sửa. Đổi riêng `dua_vao_ai` không cần duyệt lại vì không đổi nội dung hiển thị. Hệ quả: bài đã đăng vừa sửa lỗi chính tả cũng biến mất khỏi website tới khi được duyệt lại; chấp nhận để không có đường nào đưa nội dung chưa duyệt lên website (nếu cần sửa nhanh lỗi nhỏ, ghi thêm "sửa nhỏ không cần duyệt lại" ở "Việc phát sinh").
  - **`loai` không đổi được sau khi tạo** vì đổi loại là cách vòng qua bước duyệt (đổi bài sức khỏe thành FAQ để đăng ngay).
  - **Duyệt bài gắn với bản đã đọc** (việc rà soát T2.3 để lại): `phien_ban` trong body `POST /bai-viet-cho-duyet/{id}/duyet`, lệch là `409`. Đây là thay đổi hợp đồng của route T2.3 (thân bắt buộc).
  - **Gỡ bài là `luu_tru`, không xóa:** giữ lịch sử và slug (không bao giờ dùng lại cho bài khác); đăng lại đi lại đúng quy trình của loại bài. Banner thì xóa hẳn (bảng không có `deleted_at`), kèm nhật ký.
  - **Markdown lưu nguyên văn, làm sạch khi hiển thị:** frontend dùng bộ render không chạy HTML thô và chỉ nhận liên kết an toàn (`/...`, `http(s)://`, `mailto:`), ảnh chỉ từ `/...` hoặc `http(s)://`.
  - **Ảnh banner và ảnh bìa tải lên trước khi có bản ghi** (người dùng chọn ảnh rồi mới lưu form), nên ảnh có thể mồ côi; dọn bằng job nền (T3.2, "Việc phát sinh").
  - **Công khai:** FAQ có `kem_noi_dung` để một lần gọi đủ cả trang; chính sách và FAQ xếp theo thứ tự tạo, bài sức khỏe mới trước. Không trả người soạn, người duyệt, `dua_vao_ai`.
  - **Giao diện dược sĩ duyệt** `/nhan-vien/bai-viet-cho-duyet` (mã `content.approve`), đọc toàn văn đã render rồi mới bấm duyệt.
- **Hệ quả:** spec 06 mục 3.12 (thân duyệt), 3.14; spec 09 mục 2.1, 2.2, 2.3; `modules/noi_dung_web/`; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.


## QĐ-22: Nhà cung cấp, phiếu nhập và dịch vụ tồn kho (2026-10-16, task T3.1)
- **Quyết định:**
  - **Cùng số lô nhưng khác hạn sử dụng bị CHẶN** (`409 TRUNG_DU_LIEU`), theo lộ trình T3.1; KHO02 ở spec 05 chỉ nói "cảnh báo". Số lô của nhà sản xuất chỉ có một hạn, khác nhau gần như chắc là nhập nhầm và hạn sai là rủi ro an toàn thuốc.
  - **Hạn sử dụng ngắn là cảnh báo cần xác nhận** (`409 CAN_XAC_NHAN_CANH_BAO`, gửi lại với `xac_nhan_canh_bao = true`), không chặn. Hạn đã qua là `400`.
  - **Giá vốn một đơn vị cơ sở làm tròn về đồng** (`lam_tron_vnd`, CLAUDE.md quy tắc 5, như seed); thuốc viên rất rẻ mất một ít độ chính xác. Giá bình quân gia quyền lấy trọng số `so_luong_ton` (hàng đang bán); lô chưa có hàng bán lấy giá dòng nhập.
  - **Nhà cung cấp:** ngừng hợp tác là xóa mềm có `hop-tac-lai` để sửa nhầm (mã số thuế duy nhất kể cả với nhà cung cấp đã ngừng).
  - **Tra cứu sản phẩm cho phiếu nhập** (`/phieu-nhap/tra-cuu-san-pham`, quyền `stock.import`) để kho chọn dòng và quét mã vạch mà không cần quyền quản lý sản phẩm.
  - **`ton_kho.giu_hang_nhieu`:** đơn nhiều dòng giữ hàng trong MỘT lần khóa mọi lô ứng viên theo id tăng dần (FEFO chỉ quyết định thứ tự lấy sau khi đã khóa), thiếu hàng ở dòng nào thì không đổi gì. Bất biến 4 và 5 (liên quan đơn hàng) thêm vào `tests/bat_bien` ở T4.4.
  - **Rà soát nghiệp vụ gộp theo giai đoạn** (một lần cho T3.1 đến T3.5) để tiết kiệm chi phí, theo yêu cầu của người dùng.
- **Hệ quả:** spec 06 mục 3.15 và bảng mã lỗi (`CAN_XAC_NHAN_CANH_BAO`, `LO_KHONG_NHAP_DUOC`); `modules/kho/`; `tests/bat_bien/`.

## QĐ-23: Giỏ hàng và sổ địa chỉ (2026-10-16, task T4.1)
- **Quyết định:**
  - **Giỏ không giữ hàng;** tồn chỉ bị giữ khi đặt hàng (T4.4). Giỏ chỉ cảnh báo (`ton_kha_dung_don_vi`), không từ chối vì hết hàng.
  - **Một hàm kiểm tra cho mọi đường vào giỏ** (thêm, sửa, gộp): thuốc kê đơn bị chặn ở service (`422 THUOC_KE_DON_KHONG_VAO_GIO`), kể cả khi sản phẩm bị đổi loại về sau (dòng đã lưu hiện `mua_duoc = false`, không tính vào tạm tính). Không có ràng buộc CSDL chéo bảng cho việc này (CHECK không tham chiếu bảng khác); chấp nhận chặn ở service như quy tắc 6 cho phép.
  - **Giới hạn mua tính theo đơn vị cơ sở trên cả sản phẩm** (cộng mọi đơn vị): 2 hộp (20 viên) + 6 viên vượt giới hạn 25. Thêm/sửa vượt giới hạn là `422 VUOT_SO_LUONG_TOI_DA`; riêng gộp giỏ vãng lai thì CẮT về mức còn được thêm (làm tròn xuống theo đơn vị của dòng), hết chỗ thì bỏ qua dòng và báo trong `bo_qua`, để một dòng xấu không làm hỏng cả lần đăng nhập.
  - **Giỏ vãng lai chỉ lưu `{san_pham_id, don_vi_id, so_luong}` ở localStorage;** tên, giá và cờ mua được luôn do máy chủ dựng lại (`POST /gio-hang/xem`, không lưu gì), nên giá cũ trong trình duyệt không bao giờ được dùng để tính tiền.
  - **Gộp giỏ chạy một lần khi phát hiện khách đã đăng nhập** (kể cả lấy lại phiên lúc tải trang), thành công mới xóa giỏ cục bộ; lỗi mạng thì giữ lại để thử lần sau.
  - **Gợi ý "thường mua cùng"** loại thuốc kê đơn và sản phẩm không hiển thị ngay ở truy vấn; chưa có luật thì trả rỗng và giao diện ẩn mục.
  - **Sổ địa chỉ:** tối đa 10; tên tỉnh/xã do máy chủ điền từ danh mục địa giới (không tin client); khóa dòng khách khi sửa để luôn đúng một địa chỉ mặc định; danh mục địa giới T4.1 là bản giả (file JSON, spec 08 mục 8), bản GHN thêm cùng adapter vận chuyển (T4.7).
  - **Chưa làm (KTV01):** sửa hồ sơ cá nhân và đổi mật khẩu của khách (spec 06 chưa có API `PATCH /toi`); ghi ở "Việc phát sinh".
- **Hệ quả:** spec 06 mục 3.20; `modules/gio_hang/`, `modules/dia_chi/`, `tich_hop/van_chuyen/`; `frontend/src/khu/cua-hang/{gio-hang,tai-khoan}`; `test/render.tsx` bọc `<App>` của antd.

## QĐ-24: Máy trạng thái đơn hàng (2026-10-16, task T4.2)
- **Quyết định:**
  - **Bảng chuyển là dữ liệu** (`BANG_CHUYEN`, theo số dòng spec 04 mục 1.1); mọi dòng và mọi cặp ngoài bảng đều có test tham số hóa. Sai tác nhân (`403`) tách khỏi sai cặp trạng thái (`409`).
  - **Điều kiện cột "Điều kiện" được kiểm trong máy trạng thái** thay vì để nơi gọi tự nhớ: thuốc kê đơn không vào dòng 1, 2, 4, 5 (SQL), hạn xác nhận/thanh toán, đơn chưa thanh toán khi hủy, nhận tại nhà thuốc, lý do bắt buộc. Hệ quả: dòng 3 (đơn từ đơn thuốc) và 6 (bán tại quầy) được phép có thuốc kê đơn; cổng kê đơn của chúng do T5.x/T4.8 chặn.
  - **Admin không có dòng nào** trong bảng: spec 04 chỉ liệt kê dược sĩ, kho, khách, hệ thống. Cần Admin hủy đơn thì phải sửa spec trước.
  - **Tạo đơn qua `khoi_tao_trang_thai`:** cột `trang_thai` không null nên hàm này là chỗ duy nhất gán trạng thái đầu; test quét mã nguồn bằng AST (gán `.trang_thai` của đơn, `DonHang(trang_thai=...)`, `update(DonHang).values(trang_thai=...)`, SQL thô) và chỉ cho `trang_thai.py`.
  - **Tác động qua hook đăng ký** (`dang_ky_hook`) để task sau thêm thanh toán, hoàn tiền, mã giảm giá, vận đơn, thông báo mà không sửa máy trạng thái. Dòng 27 (kiểm hàng hoàn: hoàn nhập hay biệt trữ) chưa có hook, thuộc KHO10.
- **Hệ quả:** spec 04 mục 1.1 (phần Cài đặt); `modules/ban_hang/trang_thai.py`; `tests/ban_hang/`; `backend/CLAUDE.md`.


## QĐ-25: Khuyến mãi và mã giảm giá (2026-10-16, task T4.3)
- **Quyết định:**
  - Kiểm tra mã (`kiem_tra_ma`) chỉ đọc, không giữ lượt; lượt chỉ tăng khi đặt đơn qua `dung_ma` (khóa khuyến mãi FOR UPDATE), trả lại bằng hook khi đơn hủy/hết hạn (các dòng 9, 12, 14, 15, 19, 21, 27).
  - Lý do không áp dụng trả bằng `ma_ly_do` ổn định để UI hiện đúng thông điệp; kiểm tra mã bị giới hạn tần suất để chống dò mã.
  - Thuốc kê đơn không bao giờ nằm trong cơ sở giảm.
- **Hệ quả:** spec 06 mục 3.21; `modules/khuyen_mai/`; `frontend/src/khu/quan-tri/khuyen-mai`, `khu/cua-hang/gio-hang/OMaGiamGia`.

## QĐ-26: Đặt hàng online và Idempotency-Key (2026-10-16, task T4.4)
- **Quyết định:**
  - Đơn luôn dựng từ giỏ đã lưu của khách (khóa dòng giỏ đầu tiên, nên hai lần đặt của một khách nối đuôi nhau); mọi dòng phải mua được, có dòng không hợp lệ thì trả đúng lỗi của dòng đó thay vì lặng lẽ bỏ dòng.
  - Lỗi ở bước nào cũng hoàn tác cả transaction (mã giảm giá, giữ hàng, đơn); giỏ chỉ bị xóa sau khi giữ hàng thành công.
  - `tong_tien_ky_vong` là tùy chọn; có thì khác tổng tính lại là `GIA_DA_THAY_DOI` kèm bản tính lại. Frontend luôn gửi.
  - Idempotency-Key lưu trong bộ nhớ tiến trình 24 giờ, theo từng khách, kèm dấu vân tay nội dung (khác nội dung là `TRUNG_DU_LIEU`); khóa được tra SAU khi khóa giỏ và chỉ trả kết quả cũ nếu đơn đó còn tồn tại.
  - Phí ship: nhận tại nhà thuốc 0; giao tận nơi miễn phí khi `tạm tính - giảm >= mien_phi_ship_tu`, còn lại hỏi adapter, lỗi adapter dùng `phi_ship_mac_dinh`. Schema chưa có khối lượng sản phẩm nên ước lượng 20 g mỗi đơn vị cơ sở.
  - Đơn COD không có `han_xac_nhan` (spec 04 dòng 1 không quy định); đơn VNPay/MoMo có `han_thanh_toan = now + thoi_han_thanh_toan_phut`.
- **Hệ quả:** spec 06 mục 3.22; `modules/ban_hang/{dat_hang,schemas,router_khach}.py`; `core/idempotency.py`; `tests/ban_hang/test_dat_hang.py`; `frontend/src/khu/cua-hang/gio-hang/{TrangThanhToan,TrangKetQuaDatHang,thanhToan}`.

## QĐ-27: Thanh toán online, IPN và hủy quá hạn (2026-10-16, task T4.5)
- **Quyết định:**
  - Giao dịch thanh toán được tạo ở API riêng `POST /toi/don-hang/{ma_don}/thanh-toan` (Idempotency-Key), không gộp vào đặt hàng: đặt hàng xong khách vẫn có đơn dù cổng lỗi, và "thanh toán lại" dùng cùng API với khóa mới. Mã tham chiếu cổng là `ma_don-idGiaoDich`.
  - Chống trùng theo hai lớp: trạng thái giao dịch (đã khác `khoi_tao` là IPN lặp, trả mã "đã xác nhận") và `ma_giao_dich_cong` UNIQUE (cùng mã cổng trên giao dịch khác bị coi là lặp). Giao dịch rồi đơn bị khóa `FOR UPDATE` nên hai IPN đồng thời chỉ một bên chuyển trạng thái.
  - IPN thất bại không hủy đơn (còn hạn thì khách thanh toán lại). IPN thành công đến khi đơn không còn `cho_thanh_toan` (đã hủy quá hạn, hoặc đã có giao dịch khác thành công) thì ghi nhận tiền đã vào, KHÔNG đổi trạng thái đơn, tạo giao dịch `hoan_tien` `khoi_tao` và `trang_thai_tt = cho_hoan_tien`; vẫn báo cổng "đã xác nhận" để cổng ngừng gọi lại. Đơn vừa quá hạn nhưng job HT03 chưa hủy vẫn nhận thanh toán.
  - Phản hồi: VNPay `{"RspCode","Message"}` (00/01/02/04/97); MoMo `204` khi xử lý được (kể cả lặp), `400` khi sai chữ ký/số tiền/định dạng.
  - Cổng giả: `THANH_TOAN_CHE_DO` nhận `gia` hoặc `sandbox` (đúng spec 01). `POST /webhook/gia-ipn` chỉ gắn khi `gia`, không cần đăng nhập vì không có tiền thật, và đi qua cùng `xu_ly_ipn`.
  - HT03 chạy mỗi phút, hủy từng đơn qua `chuyen_trang_thai` trong savepoint riêng: đơn vừa nhận IPN (điều kiện dòng 12 không còn đúng) hoặc lỗi được bỏ qua, không làm hỏng cả lượt.
  - Hoàn tiền thật qua cổng để T6.3 (AD17); `hoan_tien` của cổng thật chưa cài.
- **Hệ quả:** spec 06 mục 3.23, 8; spec 09 (route `/thanh-toan-gia`); `tich_hop/thanh_toan/`, `modules/thanh_toan/`, `modules/ban_hang/het_han.py`, `jobs/`; `tests/thanh_toan/`; `frontend/src/khu/cua-hang/gio-hang/{TrangKetQuaDatHang,TrangCongGia,thanhToanOnline}`.

## QĐ-28: Xử lý đơn, hủy đơn và hoàn tiền khi hủy (2026-10-16, task T4.6)
- **Quyết định:**
  - Hủy đơn đã thanh toán tạo giao dịch hoàn tiền bằng một hook chung của máy trạng thái cho các dòng hủy 14, 15, 19, 21, 27 (không viết riêng ở từng route): `hoan_tien` ở `khoi_tao`, `thanh_toan_goc_id` là giao dịch thành công gần nhất, số tiền là toàn bộ số đã trả (kể cả phí vận chuyển), `trang_thai_tt = cho_hoan_tien`. Dòng 9 và 12 không cần (chưa có tiền vào; tiền đến muộn đã được HT04 xử lý ở QĐ-27).
  - Nhân viên kho chỉ thấy đơn từ "Đã xác nhận" trở đi (spec 05 DS01), cưỡng chế bằng SQL ở cả danh sách lẫn chi tiết (đơn khác là `404`, không phải `403`, để không lộ sự tồn tại). Đơn đã hủy chỉ hiện với kho nếu từng được xác nhận. Chi tiết của kho bỏ giao dịch thanh toán và `khach_hang_id`.
  - Khách bấm hủy khi đơn đã sang "Đang soạn hàng" nhận `403 KHONG_CO_QUYEN` (dòng hủy này không dành cho khách), đơn đã hủy nhận `409`. Giữ nguyên hành vi của máy trạng thái, giao diện chỉ hiện nút khi hủy được.
  - Dược sĩ không hủy được đơn `cho_thanh_toan` hoặc `cho_khach_xac_nhan` (bảng chuyển chỉ cho khách và hệ thống); muốn hủy phải đợi khách hủy hoặc hết hạn.
  - Dòng thời gian phía khách không lộ nhân viên nào xử lý; phía nội bộ có `nguoi_thuc_hien` (tên nhân viên, khách, hoặc "Hệ thống").
- **Hệ quả:** spec 06 mục 3.24; spec 04 mục 1.1; `modules/ban_hang/{dich_vu_don,router_noi_bo}.py`, hook `_tao_hoan_tien_khi_huy` ở `trang_thai.py`; `tests/ban_hang/test_xu_ly_don.py`; `frontend/src/khu/{cua-hang,nhan-vien}/don-hang/`.

## QĐ-29: Soạn hàng, vận đơn và webhook vận chuyển (2026-10-16, task T4.7)
- **Quyết định:**
  - Hàng đợi của kho dùng lại `GET /noi-bo/don-hang` (đã giới hạn đơn từ "Đã xác nhận" theo QĐ-28), API riêng `/noi-bo/soan-hang/{id}` chỉ cho chi tiết lô, đổi lô, bắt đầu soạn và đóng gói. Đóng gói cần `shipment.create`, còn lại `order.pick`.
  - Đổi lô chỉ khi đơn còn "Đã xác nhận", dời trọn phân bổ sang một lô khác (không tách lô), vì sang "Đang soạn hàng" lô đã chốt và tồn đã trừ. Muốn đổi sau đó phải hủy rồi lập lại đơn.
  - Tạo vận đơn gọi đối tác bên ngoài nên xảy ra sau khi khóa đơn và kiểm trạng thái; lỗi đối tác là `502` và đơn giữ nguyên; bước ghi lỗi sau khi đã tạo thì hủy vận đơn ở đối tác (cố gắng tối đa). Khối lượng ước tính theo `GRAM_MOI_DON_VI_CO_SO` vì schema chưa có khối lượng sản phẩm.
  - Webhook vận chuyển chịu được lặp, trễ, sai thứ tự: luôn ghi trạng thái đối tác, còn đơn đi theo đường ngắn nhất qua các bước hợp lệ (dòng 22 đến 26); sự kiện cũ không có đường đi thì bỏ qua. Chỉ vận đơn giao hàng mới nhất của đơn được đổi trạng thái đơn. Mã vận đơn không có vẫn trả `200`.
  - Trạng thái trung gian sau giao thất bại (`storing`, `sorting`...) không đưa đơn về "Đang giao"; chỉ `delivering` mới là giao lại.
  - COD giao thành công ghi `thanh_toan` COD bằng hook dòng 23, nên mọi đường dẫn tới `da_giao` bằng webhook đều ghi đúng một lần. Thu tiền khi khách nhận tại quầy (dòng 20) thuộc T4.8.
  - Màn "Giả lập vận chuyển" là bộ nút ngay trên phiếu soạn hàng khi `che_do_van_chuyen_gia` (route `/webhook/gia-van-chuyen` chỉ có ở chế độ giả).
  - Quét mã vạch là kiểm tra phía giao diện (đếm theo từng dòng, đủ số lượng mới đóng gói); backend không lưu kết quả quét. In phiếu dùng `window.print()` với CSS in.
- **Hệ quả:** spec 06 mục 3.25; spec 08 mục 5; spec 09 (`/soan-hang/:id`); `tich_hop/van_chuyen/{ghn,gia,anh_xa}.py`, `modules/ban_hang/{soan_hang,router_kho}.py`, `modules/van_chuyen/`, `ton_kho.doi_lo`; `tests/ban_hang/test_soan_hang.py`, `tests/tich_hop/test_van_chuyen.py`; `frontend/src/khu/nhan-vien/kho/{TrangSoanHang,TrangPhieuSoan,soanHang}`.

## QĐ-30: Đơn hộ khách qua điện thoại và giao đơn tại quầy (2026-10-16, task T4.8)
- **Quyết định:**
  - Đơn hộ dùng chung bộ tính tiền và giữ hàng với đặt hàng online (`dat_hang.tinh_tien`, `gio_hang.kiem_tra_dong_de_dat`) nên thuốc kê đơn, giới hạn mỗi đơn, giá, mã giảm giá và phí ship giống hệt kênh online; thuốc kê đơn bị chặn ở service, không chỉ ở giao diện.
  - Khách tra bằng đúng SĐT (không tìm gần đúng) để dược sĩ không dò danh sách khách. Server tự tra `sdt_khach`, client không gửi id khách vào đơn.
  - Đơn online (VNPay/MoMo) bắt buộc có khách có tài khoản, vì link/IPN gắn với tài khoản khách (`/toi/don-hang/{ma}/thanh-toan`); khách vãng lai chỉ COD cho tới khi có link mã truy cập (T5.3). Mã giảm giá chỉ cho khách có tài khoản (lượt dùng tính theo khách).
  - Link thanh toán trả về trong phản hồi để dược sĩ đọc/gửi khách; gửi SMS tự động thuộc KTV13. Địa chỉ giao nhập tay được chụp vào đơn, không ghi vào sổ địa chỉ của khách.
  - Thu tiền tại quầy: đơn chưa thanh toán phải chọn tiền mặt/chuyển khoản, ghi giao dịch cùng transaction với dòng 20. Hết hạn nhận tại quầy (dòng 21) là HT08 ở T4.9.
- **Hệ quả:** spec 06 mục 3.26; `modules/ban_hang/{dat_ho,giao_tai_quay,router_dat_ho,schemas_dat_ho}.py`; `/don-hang/tao` và `/giao-tai-quay` ở spec 09 đã có sẵn.

## QĐ-31: HT08 tự hoàn tất đơn và hủy đơn nhận tại quầy quá hạn (2026-10-16, task T4.9)
- **Mốc thời gian** lấy từ lịch sử trạng thái: lần chuyển gần nhất vào `da_giao` (dòng 29, hạn `thoi_han_doi_tra_ngay`) hoặc `cho_lay_hang` (dòng 21, hạn `thoi_han_nhan_tai_quay_ngay`); thiếu lịch sử thì dùng `created_at` của đơn. Đọc cấu hình mỗi lần chạy nên Admin đổi là có hiệu lực ngay.
- **Yêu cầu đổi trả mở** là mọi yêu cầu chưa `tu_choi` hoặc `hoan_tat`; còn yêu cầu mở thì đơn không tự hoàn tất.
- **Chạy mỗi 15 phút**, mỗi đơn đi qua `chuyen_trang_thai` trong savepoint riêng (hook hoàn nhập, hoàn tiền, trả lượt mã chạy như hủy thủ công). Phần nhả khóa đơn thuốc và đóng chat của HT08 làm ở T5.3, T7.4.
- **Mua lại (KTV08)** dùng lại `gop_gio` của giỏ hàng: một bộ quy tắc duy nhất cho thuốc kê đơn, ngừng bán, đơn vị, hạn mức.

## QĐ-32: Thu hồi đồng ý = xóa hồ sơ sức khỏe (2026-10-16, task T5.1)
- Spec cho khách "xóa được bất kỳ lúc nào" và "chỉ lưu khi đồng ý" nhưng chưa nói thu hồi đồng ý thì sao. Chốt: **không có trạng thái "hồ sơ còn nhưng đã thu hồi"**. Thu hồi đồng ý chính là `DELETE /toi/ho-so-suc-khoe` (xóa cứng cả hai bảng); `PUT` với `dong_y_su_dung = false` bị `400`. Hồ sơ trong DB luôn có `dong_y_su_dung = true`, nên mọi nơi đọc (cổng dược sĩ, `kiem_tra_di_ung`, lọc gợi ý AI) không cần xử lý trạng thái lửng.
- **Hàm cổng** `duoc_doc_ho_so_suc_khoe` trả `True` rồi mới ghi nhật ký; lần bị từ chối không ghi. `doc_ho_so_cho_duoc_si` là hàm đọc dữ liệu duy nhất cho dược sĩ, từ chối bằng `403 KHONG_CO_QUYEN` (không tiết lộ khách có hồ sơ hay không).
- **Khóa `KHOA_MA_HOA`**: thiếu, sai định dạng hoặc còn giá trị mẫu `doi-...` thì mã hóa/giải mã báo lỗi hệ thống; đổi khóa làm hồ sơ cũ không giải được (cần giữ khóa; xoay khóa chưa làm).
- Ghi chú dị ứng (`di_ung.ghi_chu`) có trong API nhưng giao diện T5.1 chưa cho nhập.

## QĐ-33: Gửi đơn thuốc và lưu trữ riêng tư (2026-10-16, task T5.2)
- **Vùng riêng tư** của `core/luu_tru.py` là thư mục `rieng_tu/` (tách khỏi `cong_khai/`, không route tĩnh nào phục vụ). **URL ký** dùng khóa con `khoa_hmac("url_ky_tep_rieng_tu")` suy ra từ `JWT_SECRET`, nên biến `LUU_TRU_KHOA_KY` trong `.env.example` không còn dùng.
- **Quyền ở lúc cấp URL, không ở lúc đọc:** thẻ `<img>` không gửi được token, nên file riêng tư đọc bằng URL ký (hạn 10 phút) và chỉ chủ yêu cầu (hoặc dược sĩ đang xử lý, T5.3) được nhận URL. Frontend không giữ lại URL cũ.
- **Giới hạn spam:** 5 yêu cầu mỗi SĐT mỗi 24 giờ (hằng số trong mã, chưa đưa vào cấu hình Admin).
- **`hash_anh`:** SHA-256 nội dung ảnh; nhiều ảnh thì băm các hash đã sắp xếp (cùng bộ ảnh, khác thứ tự vẫn trùng). Chỉ dùng để cảnh báo ở T5.3, không phải khóa duy nhất.
- **Khách vãng lai** không có API xem lại yêu cầu; kết quả và link xác nhận gửi qua SMS ở T5.3. AI06 đọc ảnh (`ket_qua_ai`, `ct_yeu_cau_don_thuoc`) làm ở T7.6.

## QĐ-34: Duyệt đơn thuốc, tạo đơn và xác nhận của khách (2026-10-16, task T5.3)
- **Thuốc kê đơn chỉ vào đơn qua DS05:** `kiem_tra_dong_de_dat(..., cho_phep_ke_don=True)` mặc định `False`; chỉ `tao_don` của đơn thuốc bật, và dược sĩ đó phải đang khóa yêu cầu. Giỏ hàng, đặt hàng, đơn hộ (DS07) giữ nguyên chặn. Đơn từ đơn thuốc không có mã giảm giá.
- **Phí ship tính lúc khách xác nhận,** không lúc tạo đơn (chưa biết địa chỉ); lúc tạo đơn `phi_van_chuyen = 0`, `tong_tien = tam_tinh`. Khách thấy "Tính sau khi chọn địa chỉ".
- **Link mã truy cập:** token 256 bit ngẫu nhiên, chỉ lưu SHA-256. Link luôn XEM được đơn (trang kết quả thanh toán của khách vãng lai cần đọc lại sau khi cổng đưa về), các thao tác kiểm trạng thái và hạn. SMS gửi lỗi không làm hỏng nghiệp vụ (dược sĩ vẫn thấy link trong phản hồi).
- **Khách vãng lai thanh toán online:** `tao_thanh_toan_don` dùng chung với thành viên; khóa chống trùng của vãng lai là `-don.id`. Trước khi sang cổng, trang lưu token vào `sessionStorage` để trang `/thanh-toan/ket-qua` đọc đơn qua link.
- **Khóa yêu cầu:** hết hạn (HT08) thì về `cho_duyet`. Khi đơn bị hủy trước xuất kho yêu cầu về `dang_tu_van` giữ nguyên dược sĩ và đặt lại `khoa_luc`, nên nếu dược sĩ bỏ đi thì HT08 trả về hàng chờ sau thời gian khóa. Hủy SAU khi đã xuất kho giữ `da_su_dung = true`.
- **Chưa làm (để task sau):** dược sĩ tự nhập `ct_yeu_cau_don_thuoc` (AI06 ở T7.6 điền), gợi ý thuốc thay thế cùng hoạt chất (tìm theo hoạt chất đã có), thông báo cho dược sĩ khi có yêu cầu mới (KTV13/T6.5).

## QĐ-35: Bán tại quầy POS (2026-10-16, task T5.4)
- **Không dùng giỏ hàng.** POS tạo đơn từ danh sách dòng của quầy, dùng lại `kiem_tra_dong_de_dat(cho_phep_ke_don=True)`, `tinh_tien` và `khoi_tao_trang_thai`. Thuốc kê đơn bán được nhưng luôn gắn yêu cầu đơn thuốc kênh `tai_quay` do chính dược sĩ lập (kiểm ở service, không chỉ ở giao diện).
- **Không có mã giảm giá ở quầy** và khách lẻ không cần tài khoản; gắn khách chỉ để tích lịch sử mua và đối chiếu dị ứng.
- **Xuất kho đúng thứ tự của dòng 6:** đơn vào `hoan_tat` trước, rồi giữ và xuất kho trong cùng transaction (lỗi `HET_HANG` hoàn tác tất cả). Lô `can_han` được dùng, lô hết hạn hoặc ngừng bán thì không.
- **Tiền thối chỉ có lúc bán:** DB không có cột "tiền khách đưa" nên không đổi schema; hóa đơn in lại không có hai số này. Tên nhà thuốc trên hóa đơn là hằng số `Nhà thuốc AI` (chưa có cấu hình thông tin cửa hàng).
- **`da_su_dung`** của yêu cầu quầy bật ngay khi đơn hoàn tất (spec 04 mục 6).

## QĐ-36: Yêu cầu đổi trả (2026-10-16, task T6.1)
- **Không đổi schema.** Tài khoản nhận hoàn của khách được nhập SAU khi giao dịch hoàn (`hoan_tien`, `khoi_tao`) đã có và lưu ở `thanh_toan.thong_tin_nhan_hoan`; nới thời điểm "dòng 3" trong spec để khách không phải nhập khi chưa chắc được duyệt. Chỉ áp dụng khi cổng gốc là `cod`, `tien_mat`, `chuyen_khoan`; VNPay/MoMo hoàn qua adapter.
- **Số tiền hoàn** tính lúc duyệt và kiểm lại lúc tạo giao dịch: tổng `lam_tron(thanh_tien × sl_trả / so_luong)` của các dòng, cộng phí vận chuyển nếu trả toàn bộ mọi dòng; tổng đã hoàn không vượt tổng đã thanh toán (`HOAN_VUOT_SO_DA_TRA`).
- **Bằng chứng:** ảnh ≤ 5 MB, mp4 ≤ 30 MB, tối đa 8 tệp, lưu `rieng_tu`.
- **Vận đơn trả** chỉ tạo cho đơn giao tận nơi; đơn nhận tại quầy không có.
- **Từ chối sau khi kho nhận** cần `ket_qua_kiem_hang` do kho ghi (T6.2).
- **Đơn thay thế (dòng 30):** tổng 0đ, `cod`, `da_thanh_toan`, `don_hang_goc_id`, giữ hàng FEFO; thêm dòng 30 vào bảng chuyển trạng thái để phân biệt với dòng 4.

## QĐ-37: Nhận hàng trả về và hàng hoàn (2026-10-16, task T6.2)
- **Đơn vị:** `so_luong_nhan` tính theo đơn vị của dòng đơn (cùng đơn vị khách trả); tồn cộng `so_luong_nhan x he_so`.
- **Hàng khách trả luôn vào biệt trữ** (dù nguyên vẹn), vì đã qua tay khách; không bán lại. Xử lý tiếp bằng phiếu hủy hoặc xuất trả NCC.
- **Một lô cho mỗi dòng:** schema `ct_yeu_cau_doi_tra` chỉ có một `lo_id`, nên kho chọn một lô trong các lô đã xuất cho dòng đó.
- **Hoàn tiền/đơn thay thế theo số thực nhận** (`min(trả, nhận)`); không nhận được hàng nào thì dược sĩ chỉ có thể từ chối.
- **Hàng hoàn kiểm theo từng dòng đơn** (nguyên niêm phong hoặc hư hỏng); hàng đã qua tay vận chuyển nhưng niêm phong nguyên vẹn thì hoàn nhập đúng lô.
- **Kho không thấy thông tin khách** trong màn nhận hàng.

## QĐ-38: Xác nhận hoàn tiền (2026-10-16, task T6.3)
- **Hoàn do hủy đơn** không có yêu cầu đổi trả nên khách không có chỗ nhập tài khoản: Admin chuyển về tài khoản đã dùng khi thanh toán và đính kèm chứng từ. Chỉ hoàn do đổi trả mới bắt buộc tài khoản khách nhập (QĐ-36).
- **Chứng từ** là ảnh (jpeg/png/webp, 5 MB) ở vùng `rieng_tu`, chỉ Admin xem qua URL ký.
- **Ẩn danh hóa:** sau khi hoàn xong `thong_tin_nhan_hoan` chỉ giữ ngân hàng và 4 số cuối, bỏ tên chủ tài khoản.
- **Mã hoàn của bản giả** có hậu tố ngẫu nhiên: nhiều lần hoàn một phần trên cùng giao dịch gốc không đụng ràng buộc duy nhất của `ma_giao_dich_cong`.
- **Cổng lỗi** không đổi trạng thái gì (giao dịch vẫn `khoi_tao`, Admin thử lại được). Không có thao tác "từ chối hoàn" vì spec không định nghĩa.

## QĐ-39: Đánh giá và hỏi đáp (2026-10-16, task T6.4)
- **Hậu kiểm:** đánh giá hiện ngay, dược sĩ ẩn khi vi phạm; ẩn không xóa dữ liệu và khách thấy nhãn "đang bị ẩn".
- **Đánh giá không sửa/xóa** bởi khách (spec chỉ cho phép một lần); câu hỏi sửa/xóa được khi chưa trả lời.
- **Dược sĩ phản hồi đánh giá** dùng cột `phan_hoi` có sẵn; trả lời lại câu hỏi là sửa câu trả lời và không báo khách lần nữa.
- **Giới hạn:** 10 câu hỏi/khách/24 giờ; ảnh đánh giá 3 ảnh, 5 MB, công khai.
- **Chỉ dược sĩ** kiểm duyệt (Admin có mã quyền cũng bị chặn ở service, spec 03 mục 7).

## QĐ-40: Thông báo của khách và nhắc mua lại (2026-10-16, task T6.5)
- **Kênh theo loại sự kiện** là bảng cố định trong code (`KENH_THEO_LOAI`), chưa có tùy chọn bật/tắt của khách (spec không có).
- **Không đưa nội dung nhạy cảm ra ngoài:** SMS chỉ gồm tiêu đề không dấu; email escape HTML; thông báo hỏi đáp không chứa nội dung trả lời.
- **Dedupe nhắc mua lại** nhờ `lien_ket` chứa id dòng đơn, không thêm cột/bảng. Mua lại sản phẩm làm lần mua mới thành mốc tính, nhắc cũ không lặp.
- **Ngày giao** lấy từ mốc `da_giao` mới nhất trong `lich_su_trang_thai`.
- Tắt `gui_ngoai` trong test bằng kênh ghi nhớ (fixture autouse), test không chạm SMTP.

## QĐ-41: Thu hồi lô (2026-10-16, task T6.6)
- **Gỡ khỏi đơn chưa xuất** dùng lại `_phan_bo_lai` của HT01 (nhả phân bổ `dang_giu`, giữ lại FEFO từ lô khác, đơn thiếu hàng báo kho). Hàng đã xuất kho nhưng chưa giao tới khách vẫn vào danh sách truy vết, dược sĩ liên hệ như khách đã nhận.
- **Đóng lệnh do Admin** và chỉ khi hết khách chưa liên hệ và hết hàng ở các lô (đối chiếu tồn thật, không cần liên kết từng phiếu). `khong_lien_lac_duoc` và `da_hen_tra_hang` tính là đã xử lý.
- **Không đổi schema:** phiếu hủy không có cột liên kết lệnh (nhận biết qua lô và `ly_do = thu_hoi`); phiếu xuất trả dùng cột `lenh_thu_hoi_id` có sẵn.
- **Đơn vãng lai** nhận SMS tối giản (mã đơn) qua SĐT người nhận; đơn POS không có SĐT chỉ hiện trong danh sách để dược sĩ ghi "không liên lạc được".
- **Quyền:** Admin xem lệnh, phía kho và phía liên hệ (kể cả danh sách khách, mức `chi_xem`), chỉ dược sĩ ghi kết quả liên hệ.

