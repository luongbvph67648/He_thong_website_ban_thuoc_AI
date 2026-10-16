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
