# 04. Nghiệp vụ

## 1. Bảng chuyển trạng thái
- Các bảng dưới đây là **đặc tả bắt buộc**. Service máy trạng thái phải cài đúng các dòng này và từ chối mọi chuyển trạng thái khác (`CHUYEN_TRANG_THAI_KHONG_HOP_LE`).
- Cột "Ai thực hiện" là tác nhân hợp lệ. Hệ thống (job, IPN, webhook) chạy với `nguon` tương ứng.
- Mỗi lần chuyển trạng thái đơn hàng ghi 1 dòng `lich_su_trang_thai`, với `nguon` là một trong:
  - `nguoi_dung`
  - `he_thong`
  - `webhook_van_chuyen`
  - `ipn_thanh_toan`

### 1.1 Đơn hàng - don_hang.trang_thai

Trạng thái kết thúc: Hoàn tất, Đã hủy. Mọi chuyển trạng thái đi qua HT06 và ghi lich_su_trang_thai (nguồn: nguoi_dung, he_thong, webhook_van_chuyen, ipn_thanh_toan). Chuyển trạng thái không có trong bảng thì bị từ chối.

| # | Từ trạng thái | Hành động / sự kiện | Đến trạng thái | Ai thực hiện | Mã CN | Điều kiện | Tác động dữ liệu |
|---|---|---|---|---|---|---|---|
| 1 | (tạo mới) | Đặt hàng online, chọn COD | Chờ xác nhận | Khách thành viên | KTV02 | Giỏ không có thuốc kê đơn; đủ tồn khả dụng ở lô đang bán | phan_bo_lo dang_giu theo FEFO; lo_thuoc.so_luong_giu tăng; tăng lượt mã giảm giá |
| 2 | (tạo mới) | Đặt hàng online, chọn VNPay/MoMo | Chờ thanh toán | Khách thành viên | KTV02, KTV03 | Như trên | Như trên; han_thanh_toan = hiện tại + cấu hình |
| 3 | (tạo mới) | Tạo đơn từ đơn thuốc | Chờ khách xác nhận | Dược sĩ | DS05 | Yêu cầu đơn thuốc đang tư vấn, checklist đạt | Giữ hàng; han_xac_nhan; token_truy_cap_hash nếu khách vãng lai; yêu cầu -> Đã tạo đơn |
| 4 | (tạo mới) | Tạo đơn qua điện thoại, COD | Đã xác nhận | Dược sĩ | DS07 | Không có thuốc kê đơn | Giữ hàng; nhan_vien_tao_id |
| 5 | (tạo mới) | Tạo đơn qua điện thoại, thanh toán online | Chờ thanh toán | Dược sĩ | DS07 | Không có thuốc kê đơn | Giữ hàng; gửi link thanh toán |
| 6 | (tạo mới) | Bán tại quầy | Hoàn tất | Dược sĩ | DS08 | Thanh toán đủ; thuốc kê đơn có yêu cầu kênh tại quầy | phan_bo_lo da_xuat ngay (được dùng lô cận hạn); trừ so_luong_ton; bien_dong_kho xuat_ban; thanh_toan thành công |
| 7 | Chờ khách xác nhận | Khách xác nhận, chọn COD | Đã xác nhận | Khách (tài khoản hoặc link mã truy cập) | KTV07 | Trước han_xac_nhan | phuong_thuc_tt = cod |
| 8 | Chờ khách xác nhận | Khách xác nhận, chọn VNPay/MoMo | Chờ thanh toán | Khách | KTV07 | Trước han_xac_nhan | han_thanh_toan |
| 9 | Chờ khách xác nhận | Khách từ chối / quá han_xac_nhan | Đã hủy | Khách / Hệ thống | KTV07, HT03 |  | phan_bo_lo da_nha, giảm so_luong_giu; yêu cầu đơn thuốc quay lại Đang tư vấn |
| 10 | Chờ thanh toán | IPN thành công (đơn khách tự đặt) | Chờ xác nhận | Hệ thống | HT04 | Chữ ký hợp lệ; mã giao dịch cổng chưa xử lý | thanh_toan thành công; trang_thai_tt = da_thanh_toan |
| 11 | Chờ thanh toán | IPN thành công (đơn do dược sĩ tạo) | Đã xác nhận | Hệ thống | HT04 | Như trên | Như trên |
| 12 | Chờ thanh toán | Quá han_thanh_toan / khách hủy | Đã hủy | Hệ thống / Khách | HT03, KTV06 | Chưa có IPN thành công | Nhả giữ hàng; trả lượt mã giảm giá |
| 13 | Chờ xác nhận | Dược sĩ xác nhận | Đã xác nhận | Dược sĩ | DS02 |  | nhan_vien_xac_nhan_id |
| 14 | Chờ xác nhận / Đã xác nhận | Khách hủy | Đã hủy | Khách | KTV06 | Chưa sang Đang soạn hàng | Nhả giữ hàng; trả lượt mã; đã thanh toán -> thanh_toan hoan_tien (khởi tạo), trang_thai_tt = cho_hoan_tien |
| 15 | Chờ xác nhận / Đã xác nhận | Dược sĩ hủy | Đã hủy | Dược sĩ | DS03 | Bắt buộc lý do | Như dòng trên; thông báo khách |
| 16 | Đã xác nhận | Bắt đầu soạn, chốt lô | Đang soạn hàng | Nhân viên kho | KHO03 | Lô đang bán; đổi lô phải ghi lý do | phan_bo_lo da_xuat; trừ so_luong_ton và so_luong_giu; bien_dong_kho xuat_ban; đơn thuốc liên kết da_su_dung = true |
| 17 | Đang soạn hàng | Đóng gói, tạo vận đơn | Chờ lấy hàng | Nhân viên kho | KHO04 | Giao tận nơi | van_don loai giao_hang |
| 18 | Đang soạn hàng | Đóng gói đơn nhận tại nhà thuốc | Chờ lấy hàng | Nhân viên kho | KHO04 | Nhận tại nhà thuốc | Thông báo khách đến nhận |
| 19 | Đang soạn hàng / Chờ lấy hàng | Dược sĩ hủy (hàng chưa rời kho) | Đã hủy | Dược sĩ | DS03 | Bắt buộc lý do | phan_bo_lo da_hoan_nhap; cộng so_luong_ton đúng lô; bien_dong_kho hoan_nhap; hoàn tiền nếu đã thanh toán; da_su_dung = false |
| 20 | Chờ lấy hàng | Khách nhận tại quầy | Đã giao | Dược sĩ | DS15 | Đối chiếu mã đơn/SĐT; thu tiền nếu chưa thanh toán | thanh_toan (tiền mặt/chuyển khoản) nếu thu tại quầy |
| 21 | Chờ lấy hàng | Quá hạn nhận tại quầy | Đã hủy | Hệ thống | HT08 | Nhận tại nhà thuốc | Hoàn nhập đúng lô như dòng hủy ở trên |
| 22 | Chờ lấy hàng | Đơn vị vận chuyển lấy hàng | Đang giao | Hệ thống | HT05 | Webhook | Cập nhật van_don |
| 23 | Đang giao | Giao thành công | Đã giao | Hệ thống | HT05 | Webhook | COD: thanh_toan cod thành công, trang_thai_tt = da_thanh_toan |
| 24 | Đang giao | Giao không thành công | Giao thất bại | Hệ thống | HT05 | Webhook | Thông báo khách |
| 25 | Giao thất bại | Giao lại | Đang giao | Hệ thống / Nhân viên kho | HT05, KHO04 | Đơn vị vận chuyển giao lại hoặc tạo vận đơn mới | van_don mới nếu cần |
| 26 | Giao thất bại | Đơn vị vận chuyển hoàn hàng | Hoàn về kho | Hệ thống | HT05 | Webhook |  |
| 27 | Hoàn về kho | Kho nhận và kiểm hàng hoàn | Đã hủy | Nhân viên kho | KHO10 |  | Nguyên niêm phong: hoàn nhập đúng lô (hoan_nhap). Hư hỏng: so_luong_biet_tru (nhan_tra_ve). Đã thanh toán: tạo hoàn tiền |
| 28 | Đã giao | Khách gửi yêu cầu đổi trả | (giữ Đã giao) | Khách | KTV09 | Trong thời hạn đổi trả | Tạo yeu_cau_doi_tra (xem mục 3) |
| 29 | Đã giao | Hết thời hạn đổi trả, không còn yêu cầu mở | Hoàn tất | Hệ thống | HT08 |  | Chốt doanh thu |
| 30 | (tạo mới) | Tạo đơn thay thế khi đổi trả hướng gửi hàng thay thế | Đã xác nhận | Dược sĩ | DS09 | Yêu cầu đổi trả `kho_da_nhan`, hướng `gui_hang_thay_the` | `tong_tien = 0`, `don_hang_goc_id` trỏ đơn gốc, giữ hàng FEFO; đi luồng soạn hàng từ dòng 16 |

**Cài đặt (T4.2, `modules/ban_hang/trang_thai.py`).**
- Hai điểm vào duy nhất: `khoi_tao_trang_thai` (dòng 1 đến 6, tạo đơn) và `chuyen_trang_thai(db, don, den, tac_nhan, nguon, ghi_chu)`. Bảng `BANG_CHUYEN` là dữ liệu, mỗi dòng ghi số dòng spec, trạng thái nguồn, đích, tác nhân và điều kiện. Dòng 28 (đổi trả) không đổi trạng thái đơn nên không có trong bảng.
- Tác nhân: `khach` (tài khoản; riêng dòng 7, 8, 9 cho khách vãng lai qua link mã truy cập), `duoc_si` (vai trò PHARMACIST), `kho` (WAREHOUSE), `he_thong`. Admin không có dòng nào. Người dùng thì `nguon = nguoi_dung`; hệ thống thì `he_thong`, `ipn_thanh_toan` (dòng 10, 11) hoặc `webhook_van_chuyen` (dòng 22 đến 26). Sai tác nhân là `403 KHONG_CO_QUYEN`, sai cặp trạng thái hoặc điều kiện là `409 CHUYEN_TRANG_THAI_KHONG_HOP_LE`, đơn của khách khác là `404`.
- Điều kiện được kiểm: kênh bán và phương thức thanh toán của các dòng tạo đơn; **đơn có thuốc kê đơn không đi dòng 1, 2, 4, 5** (kiểm bằng SQL trên `ct_don_hang`, quy tắc 6); trước/sau `han_xac_nhan`, `han_thanh_toan` (hệ thống chỉ hủy khi đã quá hạn); đơn chưa có thanh toán thành công khi hủy ở dòng 12; đơn khách tự đặt (dòng 10) khác đơn dược sĩ tạo (dòng 11); nhận tại nhà thuốc (dòng 20, 21); lý do bắt buộc khi dược sĩ hủy (dòng 15, 19).
- Khóa dòng đơn `FOR UPDATE` và đọc lại trạng thái trước khi chuyển, nên bấm hai lần chỉ chạy một lần. Tác động kho đã cài sẵn: nhả giữ hàng (dòng 9, 12, 14, 15, 19, 21), xuất kho khi bắt đầu soạn (16), hoàn nhập đúng lô khi hủy sau khi đã xuất (19, 21). Đã cài thêm: đánh dấu đã thanh toán (dòng 10, 11), trả lượt mã giảm giá (9, 12, 14, 15, 19, 21, 27), tạo giao dịch hoàn tiền khi hủy đơn đã thanh toán (14, 15, 19, 21, 27). Các tác động còn lại (vận đơn, thông báo, hoàn nhập khi nhận hàng trả ở dòng 27) gắn bằng `dang_ky_hook(so_dong, hook)` ở task tương ứng và chạy trong cùng transaction.

### 1.2 Yêu cầu đơn thuốc - yeu_cau_don_thuoc.trang_thai

Ảnh đơn lưu ở kho file riêng tư; hash_anh dùng để cảnh báo đơn đã dùng.

| # | Từ trạng thái | Hành động / sự kiện | Đến trạng thái | Ai thực hiện | Mã CN | Điều kiện | Tác động dữ liệu |
|---|---|---|---|---|---|---|---|
| 1 | (tạo mới) | Khách gửi ảnh đơn (vãng lai xác thực OTP) | Chờ duyệt | Khách | KVL08, KTV07 |  | AI06 đọc ảnh -> ket_qua_ai, ct_yeu_cau_don_thuoc |
| 2 | (tạo mới) | Dược sĩ nhập đơn khi bán tại quầy | Đã tạo đơn | Dược sĩ | DS08 | kenh = tai_quay | Liên kết đơn POS |
| 3 | Chờ duyệt | Dược sĩ nhận xử lý (khóa) | Đang tư vấn | Dược sĩ | DS04 | Chưa ai khóa | duoc_si_id, khoa_luc |
| 4 | Đang tư vấn | Quá thời gian khóa không xử lý | Chờ duyệt | Hệ thống | HT08 |  | Xóa duoc_si_id |
| 5 | Đang tư vấn | Checklist đạt, tạo đơn | Đã tạo đơn | Dược sĩ | DS04, DS05 | Đủ checklist; ảnh không trùng đơn đã dùng; đã xử lý cảnh báo dị ứng/tương tác | Tạo don_hang Chờ khách xác nhận |
| 6 | Đang tư vấn | Đơn không hợp lệ | Từ chối | Dược sĩ | DS04 | Bắt buộc lý do | Thông báo / SMS cho khách |
| 7 | Chờ duyệt / Đang tư vấn | Khách hủy | Khách hủy | Khách | KTV07 |  |  |
| 8 | Đã tạo đơn | Đơn liên kết bị hủy / hết hạn trước khi xuất kho | Đang tư vấn | Hệ thống | HT03, HT06 |  | Cho phép tạo lại đơn; da_su_dung vẫn false |
| 9 | Đã tạo đơn | Đơn liên kết sang Đang soạn hàng | (giữ) | Hệ thống | HT06 |  | da_su_dung = true |

### 1.3 Đổi trả & hoàn tiền - yeu_cau_doi_tra.trang_thai (thay cho "Quy trình hoàn trả tiền" bản gốc)

Hàng ở khu biệt trữ được xử lý tiếp bằng phiếu hủy (KHO09) hoặc phiếu xuất trả NCC (KHO11), cả hai cần Admin duyệt (AD12).

| # | Từ trạng thái | Hành động / sự kiện | Đến trạng thái | Ai thực hiện | Mã CN | Điều kiện | Tác động dữ liệu |
|---|---|---|---|---|---|---|---|
| 1 | (tạo mới) | Khách gửi yêu cầu: dòng và số lượng trả, lý do, ảnh/video | Chờ duyệt | Khách | KTV09 | Đơn Đã giao; trong thời hạn; tổng số lượng trả không vượt số đã mua | yeu_cau_doi_tra, ct_yeu_cau_doi_tra |
| 2 | Chờ duyệt | Xác minh không đúng | Từ chối | Dược sĩ | DS09 | Bắt buộc lý do | Thông báo khách |
| 3 | Chờ duyệt | Xác minh đúng, chọn hướng xử lý | Đã duyệt | Dược sĩ | DS09 | Chọn huong_xu_ly | Tạo van_don loai tra_hang, gửi mã cho khách; COD/tiền mặt: khách nhập tài khoản nhận hoàn |
| 4 | Đã duyệt | Kho nhận và kiểm hàng | Kho đã nhận | Nhân viên kho | KHO10 |  | ct_yeu_cau_doi_tra.lo_id, so_luong_nhan; tăng so_luong_biet_tru; bien_dong_kho nhan_tra_ve; ket_qua_kiem_hang |
| 5 | Kho đã nhận | Kiểm không đạt (không đúng mô tả) | Từ chối | Dược sĩ | DS09 | Kèm bằng chứng kiểm hàng | Thông báo khách |
| 6 | Kho đã nhận | Hướng hoàn tiền: tạo giao dịch hoàn | (giữ) | Dược sĩ | DS09 | so_tien_hoan = tổng thanh_tien các dòng trả (đã trừ giam_gia_phan_bo) | thanh_toan loai hoan_tien (khởi tạo), yeu_cau_doi_tra_id, thanh_toan_goc_id |
| 7 | Kho đã nhận | Admin hoàn tiền (API cổng hoặc chuyển khoản) | Hoàn tất | Admin | AD17 | Người xác nhận khác dược sĩ duyệt | thanh_toan hoàn tiền thành công + chung_tu_url; don_hang.trang_thai_tt = da_hoan_tien / hoan_tien_mot_phan; thông báo khách |
| 8 | Kho đã nhận | Hướng gửi hàng thay thế: tạo đơn thay thế | Hoàn tất | Dược sĩ | DS09 |  | don_hang mới tong_tien = 0, don_hang_goc_id, trạng thái Đã xác nhận -> đi luồng soạn hàng bình thường |

### 1.4 Lô thuốc - lo_thuoc.trang_thai

Đơn online chỉ dùng lô Đang bán; bán tại quầy dùng lô Đang bán và Cận hạn.

| # | Từ trạng thái | Hành động / sự kiện | Đến trạng thái | Ai thực hiện | Mã CN | Điều kiện | Tác động dữ liệu |
|---|---|---|---|---|---|---|---|
| 1 | (tạo mới) | Lập phiếu nhập lô mới | Đang bán | Nhân viên kho | KHO02 | HSD không dưới ngưỡng tối thiểu | bien_dong_kho nhap_kho |
| 2 | Đang bán | HSD còn dưới ngưỡng cận hạn | Cận hạn | Hệ thống | HT01 |  | Ngừng bán online; bán tại quầy vẫn được |
| 3 | Đang bán / Cận hạn | Hết HSD | Hết hạn | Hệ thống | HT01 |  | Khóa bán; gỡ khỏi đơn chưa xuất, phân bổ lại FEFO; chờ phiếu hủy |
| 4 | Đang bán / Cận hạn | Tạm khóa khi nghi vấn chất lượng | Khóa | Admin | AD13 | Chờ quyết định thu hồi | Không phân bổ cho đơn mới |
| 5 | Khóa | Xác minh không lỗi, mở khóa | Đang bán | Admin | AD13 |  |  |
| 6 | Bất kỳ | Có lệnh thu hồi | Thu hồi | Admin | AD13 |  | Gỡ khỏi đơn chưa xuất; liệt kê đơn đã giao qua phan_bo_lo; thông báo khách |

### 1.5 Phiếu cần duyệt - phiếu điều chỉnh, phiếu hủy, phiếu xuất trả NCC

| # | Từ trạng thái | Hành động / sự kiện | Đến trạng thái | Ai thực hiện | Mã CN | Điều kiện | Tác động dữ liệu |
|---|---|---|---|---|---|---|---|
| 1 | (tạo mới) | Nhân viên kho lập phiếu | Chờ duyệt | Nhân viên kho | KHO08, KHO09, KHO11 |  | Chưa đổi tồn |
| 2 | Chờ duyệt | Admin duyệt | Đã duyệt | Admin | AD12 | Người duyệt khác người lập | Cập nhật lo_thuoc (khu bán hoặc biệt trữ theo tu_khu); ghi bien_dong_kho |
| 3 | Chờ duyệt | Admin từ chối | Từ chối | Admin | AD12 | Bắt buộc lý do |  |

### 1.6 Hội thoại tư vấn - hoi_thoai.trang_thai

| # | Từ trạng thái | Hành động / sự kiện | Đến trạng thái | Ai thực hiện | Mã CN | Điều kiện | Tác động dữ liệu |
|---|---|---|---|---|---|---|---|
| 1 | (tạo mới) | Khách mở chat | Đang mở | Khách | KVL05 | Trong giới hạn lượt theo phiên/IP | loai = ai |
| 2 | Đang mở | AI chuyển (không chắc chắn, dấu hiệu nguy hiểm) hoặc khách bấm "Gặp dược sĩ" | Chờ dược sĩ | Hệ thống / Khách | AI04, KTV12 | Trong giờ làm việc | tom_tat |
| 3 | Đang mở | Như trên nhưng ngoài giờ | Chờ gọi lại | Hệ thống | AI04 | Ngoài giờ làm việc (cấu hình) | so_dien_thoai_goi_lai |
| 4 | Chờ dược sĩ | Dược sĩ nhận phiên | Dược sĩ đang xử lý | Dược sĩ | DS06 |  | duoc_si_id; loai = duoc_si |
| 5 | Dược sĩ đang xử lý / Chờ gọi lại | Kết thúc tư vấn / đã gọi lại | Đã đóng | Dược sĩ | DS06 |  | dong_luc |
| 6 | Đang mở | Không hoạt động quá thời gian | Đã đóng | Hệ thống | HT08 |  | dong_luc |

## 2. Quy tắc tồn kho
| Quy tắc | Nội dung | Bảng / cột |
|---|---|---|
| **Tồn khả dụng** | so_luong_ton - so_luong_giu của các lô Đang bán (đơn online); bán tại quầy tính thêm lô Cận hạn. | lo_thuoc |
| **Giữ hàng** | Tạo đơn -> phan_bo_lo dang_giu và tăng so_luong_giu; chưa đổi tồn thật nên không ghi thẻ kho. | phan_bo_lo, lo_thuoc |
| **FEFO** | Chọn lô có HSD gần nhất trước; kho đổi lô phải ghi lý do. | phan_bo_lo.ly_do_doi_lo |
| **Chốt lô** | Sang Đang soạn hàng: dang_giu -> da_xuat, trừ so_luong_ton và so_luong_giu, ghi thẻ kho xuat_ban. | phan_bo_lo, lo_thuoc, bien_dong_kho |
| **Nhả giữ** | Hủy trước khi soạn: dang_giu -> da_nha, giảm so_luong_giu. | phan_bo_lo, lo_thuoc |
| **Hoàn nhập** | Hủy khi hàng chưa rời kho, hoặc hàng hoàn nguyên niêm phong đã kiểm: da_xuat -> da_hoan_nhap, cộng so_luong_ton đúng lô, ghi thẻ kho hoan_nhap. | phan_bo_lo, lo_thuoc, bien_dong_kho |
| **Biệt trữ** | Hàng khách trả, hàng hư hỏng: cộng so_luong_biet_tru, không bán; chỉ giảm qua phiếu hủy / xuất trả đã duyệt (tu_khu = biet_tru). | lo_thuoc, ct_phieu_huy, ct_phieu_xuat_tra, bien_dong_kho |
| **Khóa ghi** | Mọi cập nhật tồn: SELECT ... FOR UPDATE trên lo_thuoc và ghi bien_dong_kho trong cùng transaction. | lo_thuoc, bien_dong_kho |
| **Báo cáo nhập - xuất - tồn** | Tồn đầu kỳ + nhập - xuất = tồn cuối kỳ, tổng hợp từ bien_dong_kho theo lô / sản phẩm / kỳ. | bien_dong_kho |

## 3. Dịch vụ tồn kho (`modules/kho/ton_kho.py`)
Mọi hàm nhận `db` đang trong transaction và tự khóa các lô liên quan (`FOR UPDATE`, theo id tăng dần).

| Hàm | Tác động | Thẻ kho (`bien_dong_kho`) |
|---|---|---|
| `nhap_kho(lo, so_luong, chung_tu)` | `so_luong_ton += n` | `nhap_kho`, khu `kho_ban`, `+n` |
| `giu_hang(ct_don_hang, so_luong_co_so, cho_phep_can_han)` | Chọn lô FEFO (mục 3.1), tạo `phan_bo_lo` `dang_giu`, `so_luong_giu += n` | Không ghi (chưa đổi tồn thật) |
| `nha_giu(phan_bo)` | `dang_giu → da_nha`, `so_luong_giu -= n` | Không ghi |
| `xuat_theo_phan_bo(phan_bo)` | `dang_giu → da_xuat`, `so_luong_ton -= n`, `so_luong_giu -= n` | `xuat_ban`, `-n` |
| `hoan_nhap(phan_bo)` | `da_xuat → da_hoan_nhap`, `so_luong_ton += n` | `hoan_nhap`, `+n` |
| `vao_biet_tru(lo, n, chung_tu)` | `so_luong_biet_tru += n` | `nhan_tra_ve`, khu `biet_tru`, `+n` |
| `tru_ton(lo, n, khu, loai, chung_tu)` | Trừ `so_luong_ton` (khu `kho_ban`, không được làm tồn khả dụng âm) hoặc `so_luong_biet_tru` | `huy_hang` / `xuat_tra_ncc`, `-n` |
| `dieu_chinh(lo, delta, chung_tu)` | `so_luong_ton += delta` (không âm, không nhỏ hơn `so_luong_giu`) | `dieu_chinh`, `±n` |

`ton_sau` của thẻ kho là giá trị sau khi cập nhật của đúng khu đó.

### 3.1 Chọn lô FEFO khi giữ hàng
```sql
SELECT id, so_luong_ton - so_luong_giu AS kha_dung
FROM lo_thuoc
WHERE san_pham_id = :sp
  AND trang_thai = ANY(:trang_thai_duoc_ban)   -- online: {dang_ban}; tại quầy: {dang_ban, can_han}
  AND han_su_dung > :hom_nay_vn
  AND so_luong_ton - so_luong_giu > 0
ORDER BY han_su_dung, id
FOR UPDATE;
```
- Lấy dần từ đầu danh sách đến khi đủ số lượng. Một dòng đơn có thể tách thành nhiều `phan_bo_lo`.
- Tổng khả dụng không đủ → `LoiNghiepVu("HET_HANG", 409, chi_tiet={"san_pham_id", "con_lai"})`, rollback toàn bộ đơn.
- `gia_von` của mỗi `phan_bo_lo` = `lo_thuoc.gia_nhap` tại thời điểm giữ.
- **Kho đổi lô khi soạn (KHO03):** nhả phân bổ cũ và giữ trên lô mới trong cùng transaction. Bắt buộc `ly_do_doi_lo`.

### 3.2 Bất biến (kiểm tra trong `tests/bat_bien/`)
1. Với mọi lô: `0 ≤ so_luong_giu ≤ so_luong_ton` và `so_luong_biet_tru ≥ 0`.
2. `so_luong_giu` của lô = tổng `so_luong_co_so` các `phan_bo_lo` `dang_giu` trên lô đó.
3. `so_luong_ton` của lô = tổng `so_luong` trên `bien_dong_kho` khu `kho_ban` của lô. Tương tự, `so_luong_biet_tru` = tổng của khu `biet_tru`.
4. Đơn ở `dang_soan_hang` trở đi (trừ `da_huy`) không còn `phan_bo_lo` `dang_giu`.
5. Với mỗi `ct_don_hang` chưa hủy: tổng `so_luong_co_so` của phân bổ (`dang_giu` hoặc `da_xuat`) = `so_luong × he_so`.

## 4. Tính tiền đơn hàng và mã giảm giá
**Thứ tự tính (mọi phép tính bằng Decimal, làm tròn về đồng ở bước cuối mỗi dòng):**
1. **Tạm tính:** `thanh_tien_goc` của mỗi dòng = `so_luong × don_gia` (`don_gia` là giá hiện tại của đơn vị lúc đặt). `tam_tinh` = tổng các dòng.
2. **Dòng hợp lệ để giảm giá** là dòng thỏa cả hai: không phải thuốc kê đơn, và thuộc phạm vi khuyến mãi (toàn bộ / danh mục kể cả danh mục con / sản phẩm). `co_so_giam` = tổng `thanh_tien_goc` các dòng hợp lệ.
3. **Điều kiện áp mã:**
   - Khuyến mãi `dang_hoat_dong` và `bat_dau ≤ now < ket_thuc`.
   - `so_luot_da_dung < tong_luot` (khi `tong_luot` khác null).
   - Số đơn chưa hủy của khách dùng mã thuộc khuyến mãi này < `luot_moi_khach`.
   - `co_so_giam ≥ don_toi_thieu`.

   Không đạt điều kiện nào thì trả `MA_GIAM_GIA_KHONG_HOP_LE` kèm lý do cụ thể.
4. **Số tiền giảm:**
   - Loại `phan_tram`: `giam = lam_tron(co_so_giam × gia_tri / 100)`, sau đó cắt ở `giam_toi_da` nếu có.
   - Loại `so_tien`: `giam = min(gia_tri, co_so_giam)`.
5. **Phân bổ giảm giá vào từng dòng hợp lệ:**
   - Mỗi dòng nhận phần giảm theo tỷ lệ `thanh_tien_goc / co_so_giam`, làm tròn xuống đồng.
   - Phần dư dồn vào **dòng hợp lệ cuối cùng**, để tổng `giam_gia_phan_bo` = `giam` đúng tuyệt đối.
   - `thanh_tien = thanh_tien_goc - giam_gia_phan_bo`.
6. **Phí vận chuyển:**
   - Nhận tại nhà thuốc: 0.
   - Giao tận nơi: nếu `tam_tinh - giam ≥ mien_phi_ship_tu` thì 0; nếu không thì lấy phí từ adapter vận chuyển. Adapter lỗi thì dùng `phi_ship_mac_dinh`.
7. `tong_tien = tam_tinh - giam_gia + phi_van_chuyen`.
8. **Dùng mã khi tạo đơn:** khóa `ma_giam_gia` `FOR UPDATE`, kiểm tra lại điều kiện, `so_luot_da_dung += 1`. Đơn bị hủy (bất kỳ lúc nào) thì `so_luot_da_dung -= 1`.

**Giới hạn số lượng:** với mỗi sản phẩm, `Σ(so_luong × he_so)` trong giỏ/đơn ≤ `san_pham.so_luong_toi_da_moi_don` (nếu khác null). Vượt thì trả `VUOT_SO_LUONG_TOI_DA`.

**Giá thay đổi giữa lúc xem và lúc đặt:** server luôn tính lại theo giá hiện tại. Nếu khác tổng client gửi lên thì trả `GIA_DA_THAY_DOI` kèm giỏ đã tính lại để khách xác nhận.

## 5. Hoàn tiền
| Trường hợp | Số tiền hoàn |
|---|---|
| Hủy đơn đã thanh toán (khách, dược sĩ, hệ thống) | `tong_tien` |
| Trả hàng một phần (đổi trả hướng `hoan_tien`) | `Σ lam_tron(ct.thanh_tien × so_luong_tra / ct.so_luong)` trên các dòng trả |
| Trả toàn bộ các dòng của đơn do lỗi nhà thuốc | Như trên + `phi_van_chuyen` |
| Gửi hàng thay thế | 0 (tạo đơn thay thế `tong_tien = 0`, `don_hang_goc_id`) |

**Ghi nhận:**
- Mỗi lần hoàn tạo 1 dòng `thanh_toan` loại `hoan_tien`:
  - `trang_thai = khoi_tao`.
  - `thanh_toan_goc_id` = giao dịch thanh toán thành công của đơn (nếu thanh toán online).
  - `yeu_cau_doi_tra_id` nếu hoàn do đổi trả.
- **`don_hang.trang_thai_tt`:**
  - `cho_hoan_tien` khi có giao dịch hoàn đang `khoi_tao`.
  - Khi Admin xác nhận (AD17): `da_hoan_tien` nếu tổng đã hoàn = tổng đã thanh toán; ngược lại `hoan_tien_mot_phan`.
- **Tổng hoàn** của một đơn không bao giờ vượt tổng đã thanh toán (`HOAN_VUOT_SO_DA_TRA`).

## 6. Đơn thuốc
- **Checklist bắt buộc** (lưu `yeu_cau_don_thuoc.checklist`, mọi khóa phải `true` mới được chấp nhận):
  - `thong_tin_nguoi_benh` (họ tên, tuổi/năm sinh, địa chỉ).
  - `thong_tin_bac_si` (họ tên, chữ ký, cơ sở khám).
  - `ngay_ke_trong_hieu_luc` (ngày kê + `hieu_luc_don_thuoc_ngay` ≥ hôm nay).
  - `don_chua_su_dung` (không trùng `hash_anh` của đơn đã `da_su_dung`; trùng thì cảnh báo, dược sĩ xác nhận).
  - `da_kiem_tra_tuong_tac` (đã xem cảnh báo tương tác/dị ứng).
- **Cảnh báo** tương tác (`tuong_tac_hoat_chat`) và dị ứng (`di_ung`) được tính tự động. Mức `nghiem_trong` hoặc `chong_chi_dinh` bắt buộc dược sĩ nhập ghi chú tư vấn trước khi tạo đơn.
- **Thuốc thay thế** khi thiếu hàng: chỉ chọn sản phẩm có cùng tập hoạt chất và hàm lượng. Hệ thống gợi ý, dược sĩ quyết định.
- **`da_su_dung` = true** khi đơn liên kết chuyển sang `dang_soan_hang` (online) hoặc khi đơn POS hoàn tất.
- **AI (AI06) chỉ gợi ý.** Dược sĩ là người quyết định mọi dòng của đơn.

## 7. Mã chứng từ
| Đối tượng | Định dạng | Sinh bằng |
|---|---|---|
| Đơn hàng `ma_don` | `DH` + 8 ký tự ngẫu nhiên (A-Z, 2-9, bỏ O/I/0/1) | `secrets` + kiểm tra trùng |
| Yêu cầu đơn thuốc `ma_yeu_cau` | `YC` + 8 ký tự ngẫu nhiên | như trên |
| Yêu cầu đổi trả `ma_yeu_cau` | `DT` + 8 ký tự ngẫu nhiên | như trên |
| Phiếu nhập / kiểm kê / điều chỉnh / hủy / xuất trả | `PN` / `KK` / `DC` / `PH` / `XT` + `YY` + 6 số | `seq_<loai>` |
| Lệnh thu hồi | `TH` + `YY` + 4 số | `seq_lenh_thu_hoi` |
| Mã nhân viên | `NV` + 4 số | `seq_nhan_vien` |

Mã của khách dùng ký tự ngẫu nhiên để không đoán được thứ tự. Mã nội bộ dùng số tuần tự để dễ tra cứu.
