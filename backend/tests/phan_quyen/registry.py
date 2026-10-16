"""Registry route nội bộ: khai báo MỘT LẦN mỗi route `/api/v1/noi-bo/*` thuộc quyền nào, mức nào (spec 10 mục 3).

Thêm route nội bộ mới thì thêm vào `REGISTRY` (hoặc `CONG_KHAI` nếu là route xác thực không cần quyền). Thiếu thì
`test_registry_day_du` fail. Khai báo ở đây phải khớp `Depends(yeu_cau_quyen(ma, muc))` của chính route đó, và mã quyền
phải có trong `docs/spec/data/quyen.yaml`; test ma trận sinh các ca đúng/sai từ đúng bảng này.
"""

TIEN_TO_NOI_BO = "/api/v1/noi-bo"

# {(PHƯƠNG THỨC, đường dẫn mẫu): (mã quyền, mức)}
REGISTRY: dict[tuple[str, str], tuple[str, str]] = {
    # KHO05, KHO06: kho đầy đủ, Admin xem; dược sĩ xem tồn (không xem cảnh báo).
    ("GET", f"{TIEN_TO_NOI_BO}/ton-kho"): ("stock.view", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/khuyen-mai"): ("promotion.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/khuyen-mai"): ("promotion.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/khuyen-mai/{{km_id}}"): ("promotion.manage", "xem"),
    ("PUT", f"{TIEN_TO_NOI_BO}/khuyen-mai/{{km_id}}"): ("promotion.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/khuyen-mai/{{km_id}}"): ("promotion.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/khuyen-mai/{{km_id}}/ma"): ("promotion.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/khuyen-mai/{{km_id}}/ma/{{ma_id}}"): ("promotion.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/bao-cao/nhap-xuat-ton"): ("report.inventory", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/bao-cao/nhap-xuat-ton/excel"): ("report.inventory", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/ton-kho/{{san_pham_id}}/lo"): ("stock.view", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/canh-bao-kho"): ("stock.alert.view", "xem"),
    # KHO07 (kho ghi, Admin xem), KHO08 (chỉ kho; duyệt của Admin ở T3.4).
    ("GET", f"{TIEN_TO_NOI_BO}/kiem-ke"): ("stocktake.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/kiem-ke"): ("stocktake.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/kiem-ke/{{phieu_id}}"): ("stocktake.manage", "xem"),
    ("PUT", f"{TIEN_TO_NOI_BO}/kiem-ke/{{phieu_id}}/so-luong"): ("stocktake.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/kiem-ke/{{phieu_id}}/chot"): ("stocktake.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/kiem-ke/{{phieu_id}}"): ("stocktake.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/dieu-chinh"): ("stock_adjust.create", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/dieu-chinh"): ("stock_adjust.create", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/dieu-chinh/{{phieu_id}}"): ("stock_adjust.create", "day_du"),
    # DS01 (kho, Admin xem), DS02, DS03 (chỉ dược sĩ).
    ("GET", f"{TIEN_TO_NOI_BO}/don-hang"): ("order.view", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/don-hang/{{don_id}}"): ("order.view", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/don-hang/{{don_id}}/xac-nhan"): ("order.confirm", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/don-hang/{{don_id}}/huy"): ("order.cancel", "day_du"),
    # KHO03, KHO04 (chỉ kho).
    ("GET", f"{TIEN_TO_NOI_BO}/soan-hang/{{don_id}}"): ("order.pick", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/soan-hang/{{don_id}}/doi-lo"): ("order.pick", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/soan-hang/{{don_id}}/bat-dau"): ("order.pick", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/soan-hang/{{don_id}}/dong-goi"): ("shipment.create", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/don-ho/khach"): ("order.create_phone", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/don-ho"): ("order.create_phone", "day_du"),
    # DS04 (duyệt) và DS05 (tạo đơn từ đơn thuốc): chỉ dược sĩ.
    ("GET", f"{TIEN_TO_NOI_BO}/don-thuoc"): ("rx_request.review", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/don-thuoc/{{yc_id}}"): ("rx_request.review", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/don-thuoc/{{yc_id}}/nhan"): ("rx_request.review", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/don-thuoc/{{yc_id}}/nha"): ("rx_request.review", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/don-thuoc/{{yc_id}}/tu-choi"): ("rx_request.review", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/don-thuoc/{{yc_id}}/canh-bao"): ("rx_request.review", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/don-thuoc/{{yc_id}}/san-pham"): ("rx_order.create", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/don-thuoc/{{yc_id}}/tao-don"): ("rx_order.create", "day_du"),
    # DS08 (chỉ dược sĩ).
    ("GET", f"{TIEN_TO_NOI_BO}/pos/san-pham"): ("pos.sell", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/pos/canh-bao"): ("pos.sell", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/pos/don-thuoc"): ("pos.sell", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/pos/don"): ("pos.sell", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/pos/don/{{don_id}}/hoa-don"): ("pos.sell", "day_du"),
    # DS09 (chỉ dược sĩ; Admin xác nhận chuyển tiền ở AD17).
    ("GET", f"{TIEN_TO_NOI_BO}/doi-tra"): ("return.review", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/doi-tra/{{yc_id}}"): ("return.review", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/doi-tra/{{yc_id}}/duyet"): ("return.review", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/doi-tra/{{yc_id}}/tu-choi"): ("return.review", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/doi-tra/{{yc_id}}/hoan-tien"): ("return.review", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/doi-tra/{{yc_id}}/thay-the"): ("return.review", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/kiem-duyet/danh-gia"): ("review.moderate", "day_du"),
    ("PUT", f"{TIEN_TO_NOI_BO}/kiem-duyet/danh-gia/{{dg_id}}/hien-thi"): ("review.moderate", "day_du"),
    ("PUT", f"{TIEN_TO_NOI_BO}/kiem-duyet/danh-gia/{{dg_id}}/phan-hoi"): ("review.moderate", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/kiem-duyet/hoi-dap"): ("qa.answer", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/kiem-duyet/hoi-dap/{{hoi_id}}/tra-loi"): ("qa.answer", "day_du"),
    ("PUT", f"{TIEN_TO_NOI_BO}/kiem-duyet/hoi-dap/{{hoi_id}}/hien-thi"): ("qa.answer", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/thu-hoi"): ("recall.create", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/thu-hoi"): ("recall.create", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/thu-hoi/{{lenh_id}}"): ("recall.create", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/thu-hoi/{{lenh_id}}/dong"): ("recall.create", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/thu-hoi/thuc-hien"): ("recall.execute", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/thu-hoi/thuc-hien/{{lenh_id}}"): ("recall.execute", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/thu-hoi/lien-he"): ("recall.contact", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/thu-hoi/lien-he/{{lenh_id}}/khach"): ("recall.contact", "xem"),
    ("PUT", f"{TIEN_TO_NOI_BO}/thu-hoi/lien-he/khach/{{ct_id}}"): ("recall.contact", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/hoan-tien"): ("refund.confirm", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/hoan-tien/{{gd_id}}/xac-nhan"): ("refund.confirm", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/nhan-hang/doi-tra"): ("return.receive", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-hang/doi-tra/{{yc_id}}"): ("return.receive", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/nhan-hang/hoan-ve"): ("return.receive", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-hang/hoan-ve/{{don_id}}"): ("return.receive", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/giao-tai-quay"): ("order.pickup_handover", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/giao-tai-quay/{{don_id}}"): ("order.pickup_handover", "day_du"),
    # KHO09, KHO11 (kho lập, Admin không lập) và AD12 (Admin duyệt/từ chối; kho không duyệt).
    ("GET", f"{TIEN_TO_NOI_BO}/phieu-huy"): ("disposal.create", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/phieu-huy"): ("disposal.create", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/phieu-huy/{{phieu_id}}"): ("disposal.create", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/xuat-tra"): ("supplier_return.create", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/xuat-tra"): ("supplier_return.create", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/xuat-tra/{{phieu_id}}"): ("supplier_return.create", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/duyet-phieu"): ("stock_doc.approve", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/duyet-phieu/{{loai}}/{{phieu_id}}"): ("stock_doc.approve", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/duyet-phieu/{{loai}}/{{phieu_id}}/duyet"): ("stock_doc.approve", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/duyet-phieu/{{loai}}/{{phieu_id}}/tu-choi"): ("stock_doc.approve", "day_du"),
    # KHO01, KHO02: kho ghi, Admin xem.
    ("GET", f"{TIEN_TO_NOI_BO}/nha-cung-cap"): ("supplier.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/nha-cung-cap"): ("supplier.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/nha-cung-cap/{{nha_cung_cap_id}}"): ("supplier.manage", "xem"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/nha-cung-cap/{{nha_cung_cap_id}}"): ("supplier.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/nha-cung-cap/{{nha_cung_cap_id}}"): ("supplier.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/nha-cung-cap/{{nha_cung_cap_id}}/hop-tac-lai"): ("supplier.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/phieu-nhap"): ("stock.import", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/phieu-nhap"): ("stock.import", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/phieu-nhap/tra-cuu-san-pham"): ("stock.import", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/phieu-nhap/{{phieu_id}}"): ("stock.import", "xem"),
    # NV01, NV02: mọi nhân viên có `profile.self` ở mức đầy đủ.
    ("GET", f"{TIEN_TO_NOI_BO}/toi"): ("profile.self", "xem"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/toi"): ("profile.self", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/auth/doi-mat-khau"): ("profile.self", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/thong-bao"): ("profile.self", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/thong-bao/so-chua-doc"): ("profile.self", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/thong-bao/da-doc-tat-ca"): ("profile.self", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/thong-bao/{{thong_bao_id}}/da-doc"): ("profile.self", "day_du"),
    # AD01: chỉ Admin có `staff.manage` (day_du).
    ("GET", f"{TIEN_TO_NOI_BO}/nhan-vien"): ("staff.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-vien"): ("staff.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}"): ("staff.manage", "xem"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}"): ("staff.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}"): ("staff.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}/khoa"): ("staff.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}/mo-khoa"): ("staff.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}/dat-lai-mat-khau"): ("staff.manage", "day_du"),
    # AD18: chỉ Admin có `role.manage` (day_du).
    ("GET", f"{TIEN_TO_NOI_BO}/vai-tro"): ("role.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/vai-tro/{{ma}}"): ("role.manage", "xem"),
    ("PUT", f"{TIEN_TO_NOI_BO}/vai-tro/{{ma}}/quyen"): ("role.manage", "day_du"),
    # AD02: chỉ Admin có `customer.manage` (day_du).
    ("GET", f"{TIEN_TO_NOI_BO}/khach-hang"): ("customer.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/khach-hang/{{khach_id}}"): ("customer.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/khach-hang/{{khach_id}}/don-hang"): ("customer.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/khach-hang/{{khach_id}}/khoa"): ("customer.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/khach-hang/{{khach_id}}/mo-khoa"): ("customer.manage", "day_du"),
    # AD08: chỉ Admin có `config.manage` (day_du). AD15: chỉ Admin có `audit.view`, chỉ đọc.
    ("GET", f"{TIEN_TO_NOI_BO}/cau-hinh"): ("config.manage", "xem"),
    ("PUT", f"{TIEN_TO_NOI_BO}/cau-hinh/{{khoa}}"): ("config.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/nhat-ky"): ("audit.view", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/nhat-ky/gia-tri-loc"): ("audit.view", "xem"),
    # AD03: chỉ Admin có `category.manage` (day_du).
    ("GET", f"{TIEN_TO_NOI_BO}/danh-muc"): ("category.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/danh-muc"): ("category.manage", "day_du"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/danh-muc/{{danh_muc_id}}"): ("category.manage", "day_du"),
    ("PUT", f"{TIEN_TO_NOI_BO}/danh-muc/{{danh_muc_id}}/vi-tri"): ("category.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/danh-muc/{{danh_muc_id}}"): ("category.manage", "day_du"),
    # AD04: chỉ Admin có `product.commercial.manage` (day_du).
    ("GET", f"{TIEN_TO_NOI_BO}/san-pham"): ("product.commercial.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/san-pham/{{san_pham_id}}"): ("product.commercial.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/san-pham"): ("product.commercial.manage", "day_du"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/san-pham/{{san_pham_id}}"): ("product.commercial.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/san-pham/{{san_pham_id}}"): ("product.commercial.manage", "day_du"),
    ("PUT", f"{TIEN_TO_NOI_BO}/san-pham/{{san_pham_id}}/don-vi"): ("product.commercial.manage", "day_du"),
    ("PUT", f"{TIEN_TO_NOI_BO}/san-pham/{{san_pham_id}}/thanh-phan"): ("product.commercial.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/san-pham/{{san_pham_id}}/anh"): ("product.commercial.manage", "day_du"),
    ("PUT", f"{TIEN_TO_NOI_BO}/san-pham/{{san_pham_id}}/anh/thu-tu"): ("product.commercial.manage", "day_du"),
    ("PUT", f"{TIEN_TO_NOI_BO}/san-pham/{{san_pham_id}}/anh/{{anh_id}}/chinh"): ("product.commercial.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/san-pham/{{san_pham_id}}/anh/{{anh_id}}"): ("product.commercial.manage", "day_du"),
    # AD05: Admin day_du, dược sĩ chi_xem (`master_data.manage` không chỉ-ADMIN). Hoạt chất không có DELETE (QĐ-16).
    ("GET", f"{TIEN_TO_NOI_BO}/thuong-hieu"): ("master_data.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/thuong-hieu/{{ban_ghi_id}}"): ("master_data.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/thuong-hieu"): ("master_data.manage", "day_du"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/thuong-hieu/{{ban_ghi_id}}"): ("master_data.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/thuong-hieu/{{ban_ghi_id}}"): ("master_data.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/nha-san-xuat"): ("master_data.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/nha-san-xuat/{{ban_ghi_id}}"): ("master_data.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/nha-san-xuat"): ("master_data.manage", "day_du"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/nha-san-xuat/{{ban_ghi_id}}"): ("master_data.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/nha-san-xuat/{{ban_ghi_id}}"): ("master_data.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/hoat-chat"): ("master_data.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/hoat-chat/{{ban_ghi_id}}"): ("master_data.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/hoat-chat"): ("master_data.manage", "day_du"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/hoat-chat/{{ban_ghi_id}}"): ("master_data.manage", "day_du"),
    # DS10: dược sĩ day_du, Admin chi_xem. Thao tác ghi còn đòi người thực hiện là dược sĩ (`dam_bao_la_duoc_si`).
    ("GET", f"{TIEN_TO_NOI_BO}/chuyen-mon"): ("content.professional.edit", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/chuyen-mon/san-pham/{{san_pham_id}}"): ("content.professional.edit", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/chuyen-mon/san-pham/{{san_pham_id}}"): ("content.professional.edit", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/chuyen-mon/{{phien_ban_id}}/duyet"): ("content.approve", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/chuyen-mon/{{phien_ban_id}}/luu-tru"): ("content.professional.edit", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/tuong-tac"): ("content.professional.edit", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/tuong-tac/{{hoat_chat_1_id}}/{{hoat_chat_2_id}}"): ("content.professional.edit", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/tuong-tac"): ("content.professional.edit", "day_du"),
    ("PUT", f"{TIEN_TO_NOI_BO}/tuong-tac/{{hoat_chat_1_id}}/{{hoat_chat_2_id}}"): (
        "content.professional.edit",
        "day_du",
    ),
    ("DELETE", f"{TIEN_TO_NOI_BO}/tuong-tac/{{hoat_chat_1_id}}/{{hoat_chat_2_id}}"): (
        "content.professional.edit",
        "day_du",
    ),
    ("GET", f"{TIEN_TO_NOI_BO}/bai-viet-cho-duyet"): ("content.approve", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/bai-viet-cho-duyet/{{bai_viet_id}}"): ("content.approve", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/bai-viet-cho-duyet/{{bai_viet_id}}/duyet"): ("content.approve", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/banner"): ("cms.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/banner"): ("cms.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/banner/anh"): ("cms.manage", "day_du"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/banner/{{banner_id}}"): ("cms.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/banner/{{banner_id}}"): ("cms.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/bai-viet"): ("cms.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/bai-viet"): ("cms.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/bai-viet/anh"): ("cms.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/bai-viet/{{bai_viet_id}}"): ("cms.manage", "xem"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/bai-viet/{{bai_viet_id}}"): ("cms.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/bai-viet/{{bai_viet_id}}/go"): ("cms.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/bai-viet/{{bai_viet_id}}/dang"): ("cms.manage", "day_du"),
}

# Route nội bộ cố ý KHÔNG cần quyền vì chạy trước khi có phiên (đăng nhập) hoặc chỉ dựa vào cookie refresh.
CONG_KHAI: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", f"{TIEN_TO_NOI_BO}/auth/dang-nhap"),
        ("POST", f"{TIEN_TO_NOI_BO}/auth/lam-moi"),
        ("POST", f"{TIEN_TO_NOI_BO}/auth/dang-xuat"),
    }
)

# Chỉ hai route này được dùng khi tài khoản còn bị bắt đổi mật khẩu (`ke_ca_chua_doi_mat_khau=True`):
# đọc hồ sơ để biết phải đổi, và chính việc đổi mật khẩu. Route khác mà bật cờ này là lỗ hổng bỏ qua việc bắt đổi.
CHO_PHEP_KHI_CHUA_DOI_MAT_KHAU: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", f"{TIEN_TO_NOI_BO}/toi"),
        ("POST", f"{TIEN_TO_NOI_BO}/auth/doi-mat-khau"),
    }
)
