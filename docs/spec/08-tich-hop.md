# 08. Tích hợp bên ngoài

## 1. Nguyên tắc adapter
- Mỗi loại tích hợp có:
  - Một interface (Protocol) trong `app/tich_hop/<loai>/base.py`.
  - Bản thật: `vnpay.py`, `momo.py`, `ghn.py`, `sms.py`, `email.py`.
  - Bản giả: `gia.py`.
- Chọn bản nào bằng biến môi trường `*_CHE_DO` (spec 01 mục 5) qua hàm `lay_adapter_<loai>()`. Code nghiệp vụ chỉ biết interface.
- **Bản giả** chạy hoàn toàn offline, xác định (deterministic), có thể "bấm" kết quả để demo và test. **Test luôn dùng bản giả.**
- Gọi HTTP ra ngoài dùng `httpx.AsyncClient`:
  - Timeout 10 giây, thử lại tối đa 2 lần cho lỗi mạng/5xx với GET.
  - Không thử lại POST tạo giao dịch.
- Log mọi request/response với đối tác, đã che khóa bí mật và chữ ký. Payload thô lưu vào `thanh_toan.du_lieu_ipn` và `van_don.du_lieu_webhook`.

## 2. Thanh toán VNPay
```python
class CongThanhToan(Protocol):
    async def tao_url_thanh_toan(self, don: DonHang, giao_dich: ThanhToan, ip: str) -> str: ...
    def xac_thuc_ipn(self, tham_so: dict) -> KetQuaIpn: ...      # chữ ký, mã đơn, số tiền, mã GD cổng, thành công?
    async def hoan_tien(self, giao_dich_goc: ThanhToan, so_tien: Decimal, ly_do: str) -> KetQuaHoan: ...
```
- **Sandbox:** đăng ký tài khoản test tại trang VNPay sandbox để lấy `vnp_TmnCode` và `vnp_HashSecret`.
- **Chữ ký:**
  1. Sắp xếp tham số `vnp_*` theo tên (bỏ `vnp_SecureHash`, `vnp_SecureHashType`).
  2. URL-encode giá trị và nối thành chuỗi `k=v&...`.
  3. Tính **HMAC-SHA512** với `vnp_HashSecret`.
- **Tham số gửi đi:** số tiền gửi `vnp_Amount = tong_tien × 100`. `vnp_TxnRef` là mã duy nhất cho mỗi lần thanh toán: `ma_don` + `-` + id giao dịch, để thanh toán lại được sau khi lần trước thất bại.
- **Xử lý IPN** (`GET /api/v1/webhook/vnpay-ipn`), theo thứ tự:
  1. Kiểm chữ ký.
  2. Tìm giao dịch theo `vnp_TxnRef`.
  3. Kiểm số tiền.
  4. Nếu đã xử lý thì trả mã "đã xác nhận".
  5. Cập nhật `thanh_toan` + HT06.
  6. Trả JSON `{"RspCode": "...", "Message": "..."}` đúng bảng mã trong tài liệu VNPay.
- **Return URL** chỉ dùng để chuyển khách về trang kết quả. Trang này hỏi lại backend, **không** cập nhật đơn theo return URL.
- Kiểm tra lại định dạng tham số và bảng mã với tài liệu VNPay hiện hành khi tích hợp (ghi phiên bản API vào `12-quyet-dinh.md`).

## 3. Thanh toán MoMo
- **Sandbox:** dùng bộ `partnerCode`, `accessKey`, `secretKey` test của MoMo. API tạo giao dịch (captureWallet) trả `payUrl`.
- **Chữ ký:** **HMAC-SHA256** trên chuỗi `k=v&...` theo **đúng thứ tự trường** MoMo quy định cho từng API (tạo giao dịch, IPN, hoàn tiền khác nhau).
- **Xử lý IPN** (`POST /api/v1/webhook/momo-ipn`): giống VNPay (chữ ký → tìm giao dịch theo `orderId` → số tiền → chống trùng → cập nhật), sau đó phản hồi đúng yêu cầu của MoMo.
- **Hoàn tiền** qua API refund với `transId` gốc (lưu ở `thanh_toan.ma_giao_dich_cong`).

## 4. Bản giả của thanh toán
- `tao_url_thanh_toan` trả URL tới trang `/thanh-toan-gia?giao_dich=...` của frontend. Trang đọc thông tin giao dịch bằng `GET /api/v1/webhook/gia-giao-dich` rồi dựng giao diện **mô phỏng cổng đã chọn** (QĐ-55):
  - **VNPay:** chọn phương thức, nhập thẻ nội địa (bộ thẻ thử nghiệm của sandbox VNPay hiện ngay trên trang), OTP `123456`, hoặc quét QR giả lập; thẻ không đủ số dư và thẻ chưa kích hoạt cho giao dịch thất bại có lý do; nhập sai OTP 3 lần thì thất bại.
  - **MoMo:** mã QR, khung điện thoại giả, mã PIN `123456`; từ chối hoặc sai PIN 3 lần thì thất bại.
  - Cả hai có đồng hồ đếm ngược theo `han_thanh_toan` của đơn, nút Hủy giao dịch, màn kết quả rồi tự quay về `/thanh-toan/ket-qua`, và dòng cảnh báo "môi trường mô phỏng, không có tiền thật".
  - Giao dịch đã xử lý thì không cho thanh toán lại trên cùng trang (thanh toán lại tạo giao dịch mới).
- Khi khách hoàn tất, frontend gọi `POST /api/v1/webhook/gia-ipn`. Route này **chỉ tồn tại khi `THANH_TOAN_CHE_DO=gia`**, tạo IPN đã ký bằng khóa giả và đi qua **cùng** hàm xử lý IPN thật.
- `hoan_tien` luôn thành công và trả mã giả. Muốn kiểm cả giao thức thật (chữ ký, IPN, hoàn tiền) thì dùng `mo_phong` (mục 4b).

## 4b. Máy chủ mô phỏng VNPay, MoMo, GHN (`*_CHE_DO=mo_phong`, QĐ-56)
Cổng "giả" ở mục 4 dùng chữ ký và route riêng nên không kiểm chứng được adapter thật. Chế độ `mo_phong` thì **chạy nguyên
adapter thật** (`vnpay.py`, `momo.py`, `ghn.py`), chỉ đổi địa chỉ đối tác sang máy chủ mô phỏng nằm trong chính ứng dụng
(`app/tich_hop/mo_phong/`, route dưới `/api/v1/mo-phong`). Máy chủ mô phỏng nói đúng giao thức đối tác:
- **VNPay:** `vpcpay.html` kiểm chữ ký HMAC-SHA512 rồi chuyển khách sang trang mô phỏng; khách thao tác (thẻ thử nghiệm,
  OTP, hoặc QR) rồi máy chủ mô phỏng **gọi IPN server-to-server** (`GET /webhook/vnpay-ipn` với `vnp_*` đã ký) và trả
  `vnp_ReturnUrl` có chữ ký cho trình duyệt. Mã phản hồi `00`, `24` khách hủy, `51` không đủ số dư, `11` hết hạn, `09`
  thẻ chưa đăng ký, `12` thẻ khóa, `13` sai OTP. **Hoàn tiền** `merchant_webapi/api/transaction` (JSON, ký `|` theo thứ
  tự trường), mã `00` thành công, `91` không thấy giao dịch, `93` số tiền không hợp lệ, `97` sai chữ ký.
- **MoMo:** `POST /v2/gateway/api/create` (ký HMAC-SHA256 theo thứ tự trường) trả `payUrl`; khách xác nhận bằng PIN; IPN là
  `POST` JSON tới `ipnUrl`, cửa hàng trả HTTP 204; `resultCode` 0, 1006 từ chối, 1001 không đủ tiền, 1005 hết hạn, 13
  sai chữ ký, 22 số tiền sai (1.000 đến 50.000.000 ₫). **Hoàn tiền** `POST /v2/gateway/api/refund` theo `transId` gốc.
- **GHN:** `/shiip/public-api/v2/shipping-order/{fee,create}` và `/switch-status/cancel` với tiêu đề `Token` + `ShopId`,
  khuôn `{code, message, data}`; hủy chỉ được khi vận đơn còn `ready_to_pick`/`picking`; công cụ demo
  `POST /mo-phong/ghn/phat-su-kien` phát webhook đúng khuôn GHN kèm `Token` tới `/webhook/ghn`.
- Máy chủ mô phỏng **không lưu trạng thái riêng**: thông tin giao dịch nằm trong tham số đã ký (VNPay) hoặc token ký (MoMo),
  số liệu hoàn tiền và trạng thái vận đơn đọc từ chính CSDL của cửa hàng. Cùng `requestId` hoàn tiền thì cùng mã giao dịch
  (gọi lại không hoàn hai lần).
- Mặc định khóa/URL của chế độ này tự điền (`config.py`), không cần đăng ký tài khoản đối tác. Chuyển sang sandbox thật:
  đặt `*_CHE_DO=sandbox` (thanh toán) hoặc `ghn` (vận chuyển) và điền địa chỉ + khóa thật; không sửa code.
- **Không dùng ở production**: `MOI_TRUONG=production` từ chối cả `gia` lẫn `mo_phong`.

## 5. Vận chuyển GHN
```python
class DonViVanChuyen(Protocol):
    async def tinh_phi(self, dia_chi: DiaChiGiao, khoi_luong_gram: int, gia_tri: Decimal) -> Decimal: ...
    async def tao_van_don(self, don: DonHang, loai: Literal["giao_hang", "tra_hang"], khoi_luong_gram: int) -> KetQuaVanDon: ...
    async def huy_van_don(self, ma_van_don: str) -> None: ...
    def xac_thuc_webhook(self, headers: dict, body: dict) -> SuKienVanChuyen: ...   # ma_van_don, trang_thai_doi_tac; sai token: WebhookKhongHopLe
```
- **Chọn adapter:** `VAN_CHUYEN_CHE_DO` = `gia` (mặc định) hoặc `ghn`; thuộc tính `ten` ghi vào `van_don.don_vi_van_chuyen`. Webhook GHN xác thực bằng header `Token` = `GHN_WEBHOOK_TOKEN`.
- **Môi trường:** GHN có môi trường dev/sandbox riêng (`GHN_URL`). Header gồm `Token`, `ShopId`. Dùng API v2: tính phí, tạo đơn, hủy đơn, master data tỉnh/xã.
- **Ánh xạ trạng thái đối tác → hành động** (để trong `tich_hop/van_chuyen/ghn.py`, có test):

| Trạng thái GHN (nhóm) | Hành động |
|---|---|
| đã lấy hàng (`picked`) | HT06: `cho_lay_hang → dang_giao` |
| giao thành công (`delivered`) | HT06: `dang_giao → da_giao` (+ ghi nhận COD) |
| giao thất bại / chờ giao lại (`delivery_fail`, `waiting_to_return`) | HT06: `dang_giao → giao_that_bai` |
| đang giao lại | HT06: `giao_that_bai → dang_giao` |
| đã hoàn (`returned`) | HT06: `giao_that_bai → hoan_ve_kho` |
| hủy (`cancel`) | Chỉ ghi `van_don`, báo kho |
| trạng thái khác | Chỉ ghi `van_don.trang_thai_doi_tac` |

- **Bản giả:**
  - Phí = 20.000đ + 5.000đ mỗi 500 g vượt 1 kg.
  - Mã vận đơn giả `GIA` + số.
  - Màn nội bộ "Giả lập vận chuyển" (chỉ hiện khi chế độ `gia`) cho phép bấm phát sự kiện webhook để demo luồng giao hàng.

## 6. Lưu trữ file (`core/luu_tru.py`)
- **Hai vùng lưu trữ:**
  - `cong_khai`: ảnh sản phẩm, banner, bài viết. Phục vụ qua `GET /api/v1/tep/<khóa>` (dưới `/api/v1` để dùng chung proxy của frontend và nginx; QĐ-17).
  - `rieng_tu`: ảnh đơn thuốc, ảnh/video đổi trả, chứng từ hoàn tiền. Không phục vụ tĩnh.
- **Dev:** thư mục `LUU_TRU_THU_MUC`. Có thể thay bằng S3/MinIO sau này qua cùng interface (`luu`, `doc`, `xoa`, `url_ky(khoa, het_han)`).
- **URL ký:** `HMAC(khoa | het_han)` bằng khóa con suy ra từ `JWT_SECRET` (`khoa_hmac("url_ky_tep_rieng_tu")`, QĐ-12), hết hạn sau 10 phút. Endpoint đọc kiểm chữ ký, hạn và quyền (spec 06 mục 7).

## 7. SMS và email (OTP, thông báo)
```python
class KenhTinNhan(Protocol):
    async def gui_sms(self, so_dien_thoai: str, noi_dung: str) -> None: ...
    async def gui_email(self, den: str, tieu_de: str, noi_dung_html: str) -> None: ...
```
- **Bản giả:**
  - SMS ghi ra log (mức INFO, hiện cả mã OTP **chỉ ở chế độ giả**).
  - Email gửi qua SMTP tới Mailpit (`localhost:1025`, xem tại http://localhost:8025).
- **Bản thật:** chọn nhà cung cấp SMS brandname hoặc SMTP khi deploy; ghi lựa chọn vào `12-quyet-dinh.md`.
- **Mẫu nội dung** đặt trong `app/tich_hop/tin_nhan/mau/`. Không đưa dữ liệu sức khỏe vào SMS hoặc email.

## 8. Địa giới hành chính
- Từ 01/07/2025 Việt Nam dùng mô hình 2 cấp (tỉnh – xã). Địa chỉ lưu `ma_tinh`, `ma_phuong_xa` theo **mã của đơn vị vận chuyển**; `ma_quan_huyen` để trống nếu đối tác không dùng.
- Danh mục tỉnh/xã lấy từ API master data của GHN, cache 24 giờ. Bản giả dùng file JSON nhỏ trong `tich_hop/van_chuyen/du_lieu_gia/`.
