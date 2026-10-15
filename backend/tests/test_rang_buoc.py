"""Migration 0002: DB phải từ chối dữ liệu vi phạm từng CHECK và partial unique (docs/spec/02-database.md mục 4).

Mỗi ràng buộc được thử theo hai chiều: dòng hợp lệ (kể cả sát biên) phải chèn được, dòng vi phạm phải bị chính ràng buộc
đó từ chối. Để không phải dựng cả đồ thị khóa ngoại, test đặt `session_replication_role = replica` (tắt trigger khóa
ngoại, cần superuser: user `postgres` của docker compose và CI có quyền này); CHECK và unique index vẫn hoạt động.
Mỗi case chạy trong transaction rồi rollback, nên dùng chung một database cho cả module.

Postgres báo ràng buộc đầu tiên (theo tên) bị vi phạm, nên khi thử "đúng ràng buộc này" test gỡ các CHECK còn lại của
bảng (DDL của Postgres nằm trong transaction nên rollback là trở lại nguyên trạng).
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

CHECK_VIOLATION = "23514"
UNIQUE_VIOLATION = "23505"

NULL = "NULL"


# --- Hạ tầng dựng dòng dữ liệu --------------------------------------------------------------------------------------

# Giá trị (dạng literal SQL) cho cột bắt buộc, theo kiểu. Chỉ cần thỏa NOT NULL; ý nghĩa nghiệp vụ do BASE/case định.
_GIA_TRI_THEO_KIEU = {
    "integer": "1",
    "smallint": "1",
    "bigint": "1",
    "character varying": "'x'",
    "text": "'x'",
    "numeric": "0",
    "date": "DATE '2026-01-01'",
    "timestamp with time zone": "now()",
    "boolean": "false",
    "jsonb": "'{}'",
}

# Giá trị nền riêng của từng bảng để dòng nền thỏa MỌI CHECK của bảng đó (mặc định theo kiểu sẽ vi phạm một số CHECK).
BASE: dict[str, dict[str, str]] = {
    "thanh_toan": {"so_tien": "1"},
    "khuyen_mai": {"gia_tri": "1", "ket_thuc": "now() + interval '1 day'"},
    "khuyen_mai_pham_vi": {"san_pham_id": "1"},
    "thong_bao": {"khach_hang_id": "1"},
    "phien_dang_nhap": {"khach_hang_id": "1"},
    "tuong_tac_hoat_chat": {"hoat_chat_b_id": "2"},
    "de_xuat_nhap_hang": {"ky_ket_thuc": "DATE '2026-02-01'"},
}


async def dong_nen(conn, bang: str) -> dict[str, str]:
    """Dòng tối thiểu hợp lệ: cột bắt buộc không có default/identity lấy giá trị theo kiểu, rồi áp BASE của bảng."""
    cot = (
        await conn.execute(
            text(
                """
                SELECT column_name, data_type, udt_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :bang AND is_nullable = 'NO'
                  AND column_default IS NULL AND is_identity = 'NO'
                ORDER BY ordinal_position
                """
            ),
            {"bang": bang},
        )
    ).all()
    dong: dict[str, str] = {}
    for ten, kieu, udt in cot:
        if kieu == "USER-DEFINED":
            nhan = (
                await conn.execute(
                    text(
                        "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                        "WHERE t.typname = :udt ORDER BY e.enumsortorder LIMIT 1"
                    ),
                    {"udt": udt},
                )
            ).scalar_one()
            dong[ten] = f"'{nhan}'"
        else:
            dong[ten] = _GIA_TRI_THEO_KIEU[kieu]  # KeyError nghĩa là gặp kiểu mới: bổ sung vào bảng trên
    return {**dong, **BASE.get(bang, {})}


async def thu_chen(conn, bang: str, dong: dict[str, str]) -> tuple[str, str | None] | None:
    """Chèn một dòng trong savepoint rồi hoàn tác luôn. Trả None nếu chèn được, ngược lại (sqlstate, tên ràng buộc)."""
    cau_lenh = f"INSERT INTO {bang} ({', '.join(dong)}) VALUES ({', '.join(dong.values())})"
    try:
        async with conn.begin_nested() as savepoint:
            await conn.execute(text(cau_lenh))
            await savepoint.rollback()
    except DBAPIError as loi:
        goc = loi.orig.__cause__ or loi.orig  # lỗi asyncpg gốc
        return goc.sqlstate, goc.constraint_name
    return None


async def mo_ket_noi_thu(engine):
    """Mở kết nối với trigger khóa ngoại tắt; đóng kết nối là rollback mọi thứ."""
    conn = await engine.connect()
    await conn.execute(text("SET LOCAL session_replication_role = replica"))
    return conn


async def go_check_khac(conn, bang: str, giu_lai: str) -> None:
    ten_khac = (
        await conn.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = CAST(:bang AS regclass) AND contype = 'c' AND conname <> :giu"
            ),
            {"bang": bang, "giu": giu_lai},
        )
    ).scalars()
    for ten in list(ten_khac):
        await conn.execute(text(f"ALTER TABLE {bang} DROP CONSTRAINT {ten}"))


# --- CHECK ----------------------------------------------------------------------------------------------------------


def C(ten: str, bang: str, vi_pham: list[dict], hop_le: list[dict]):
    return pytest.param(ten, bang, vi_pham, hop_le, id=ten)


SO_LUONG_GT_0 = [
    ("ck_ct_gio_hang_so_luong_gt_0", "ct_gio_hang"),
    ("ck_ct_don_hang_so_luong_gt_0", "ct_don_hang"),
    ("ck_ct_phieu_nhap_so_luong_gt_0", "ct_phieu_nhap"),
    ("ck_ct_phieu_huy_so_luong_gt_0", "ct_phieu_huy"),
    ("ck_ct_phieu_xuat_tra_so_luong_gt_0", "ct_phieu_xuat_tra"),
    ("ck_ct_yeu_cau_doi_tra_so_luong_gt_0", "ct_yeu_cau_doi_tra"),
]

CAC_CHECK = [
    C(
        "ck_don_vi_quy_doi_he_so_ge_1",
        "don_vi_quy_doi",
        [{"he_so": "0"}, {"he_so": "-3"}],
        [{"he_so": "1"}, {"he_so": "10"}],
    ),
    C(
        "ck_don_vi_quy_doi_gia_ban_ge_0",
        "don_vi_quy_doi",
        [{"gia_ban": "-1"}],
        [{"gia_ban": "0"}, {"gia_ban": "50000"}],
    ),
    C("ck_lo_thuoc_ton_ge_0", "lo_thuoc", [{"so_luong_ton": "-1"}], [{"so_luong_ton": "0"}, {"so_luong_ton": "7"}]),
    C("ck_lo_thuoc_giu_ge_0", "lo_thuoc", [{"so_luong_giu": "-1"}], [{"so_luong_giu": "0"}]),
    C(
        "ck_lo_thuoc_giu_le_ton",
        "lo_thuoc",
        [{"so_luong_ton": "3", "so_luong_giu": "4"}],
        [{"so_luong_ton": "3", "so_luong_giu": "3"}, {"so_luong_ton": "3", "so_luong_giu": "0"}],
    ),
    C(
        "ck_lo_thuoc_biet_tru_ge_0",
        "lo_thuoc",
        [{"so_luong_biet_tru": "-1"}],
        [{"so_luong_biet_tru": "0"}, {"so_luong_biet_tru": "2"}],
    ),
    C(
        "ck_lo_thuoc_han_sau_nsx",
        "lo_thuoc",
        [
            {"ngay_san_xuat": "DATE '2026-01-01'", "han_su_dung": "DATE '2026-01-01'"},
            {"ngay_san_xuat": "DATE '2026-01-02'", "han_su_dung": "DATE '2026-01-01'"},
        ],
        [{"ngay_san_xuat": "DATE '2025-12-31'", "han_su_dung": "DATE '2026-01-01'"}, {"ngay_san_xuat": NULL}],
    ),
    *[C(ten, bang, [{"so_luong": "0"}, {"so_luong": "-1"}], [{"so_luong": "1"}]) for ten, bang in SO_LUONG_GT_0],
    C("ck_ct_phieu_nhap_co_so_gt_0", "ct_phieu_nhap", [{"so_luong_co_so": "0"}], [{"so_luong_co_so": "1"}]),
    C(
        "ck_ct_phieu_nhap_gia_nhap_ge_0",
        "ct_phieu_nhap",
        [{"gia_nhap": "-1"}],
        [{"gia_nhap": "0"}, {"gia_nhap": "12000"}],
    ),
    C("ck_phan_bo_lo_co_so_gt_0", "phan_bo_lo", [{"so_luong_co_so": "0"}], [{"so_luong_co_so": "1"}]),
    C("ck_phan_bo_lo_gia_von_ge_0", "phan_bo_lo", [{"gia_von": "-1"}], [{"gia_von": "0"}, {"gia_von": "9000"}]),
    C(
        "ck_ct_phieu_dieu_chinh_thay_doi_khac_0",
        "ct_phieu_dieu_chinh",
        [{"so_luong_thay_doi": "0"}],
        [{"so_luong_thay_doi": "-5"}, {"so_luong_thay_doi": "5"}],
    ),
    # Với don_hang, các số được chọn để mỗi dòng vi phạm chỉ đúng một ràng buộc (tong_tien luôn khớp công thức).
    C(
        "ck_don_hang_tam_tinh_ge_0",
        "don_hang",
        [{"tam_tinh": "-1", "tong_tien": "-1"}],
        [{"tam_tinh": "10", "tong_tien": "10"}],
    ),
    C(
        "ck_don_hang_giam_gia_ge_0",
        "don_hang",
        [{"giam_gia": "-1", "tong_tien": "1"}],
        [{"tam_tinh": "10", "giam_gia": "3", "tong_tien": "7"}],
    ),
    C(
        "ck_don_hang_phi_van_chuyen_ge_0",
        "don_hang",
        [{"phi_van_chuyen": "-1", "tong_tien": "-1"}],
        [{"phi_van_chuyen": "15000", "tong_tien": "15000"}],
    ),
    C(
        "ck_don_hang_tong_tien_dung",
        "don_hang",
        [{"tam_tinh": "100", "giam_gia": "10", "phi_van_chuyen": "5", "tong_tien": "100"}],
        [{"tam_tinh": "100", "giam_gia": "10", "phi_van_chuyen": "5", "tong_tien": "95"}],
    ),
    C(
        "ck_don_hang_phuong_thuc_tt_bat_buoc",
        "don_hang",
        [
            {"trang_thai": "'cho_xac_nhan'", "phuong_thuc_tt": NULL},
            {"trang_thai": "'hoan_tat'", "phuong_thuc_tt": NULL},
        ],
        [
            {"trang_thai": "'cho_xac_nhan'", "phuong_thuc_tt": "'cod'"},
            {"trang_thai": "'cho_khach_xac_nhan'", "phuong_thuc_tt": NULL},
            {"trang_thai": "'da_huy'", "phuong_thuc_tt": NULL},
        ],
    ),
    C(
        "ck_ct_don_hang_giam_gia_phan_bo_ge_0",
        "ct_don_hang",
        [{"giam_gia_phan_bo": "-1", "thanh_tien": "1"}],
        [{"giam_gia_phan_bo": "0"}],
    ),
    C(
        "ck_ct_don_hang_thanh_tien_dung",
        "ct_don_hang",
        [{"so_luong": "2", "don_gia": "100", "thanh_tien": "100"}],
        [{"so_luong": "2", "don_gia": "100", "giam_gia_phan_bo": "20", "thanh_tien": "180"}],
    ),
    C("ck_thanh_toan_so_tien_gt_0", "thanh_toan", [{"so_tien": "0"}, {"so_tien": "-1"}], [{"so_tien": "1"}]),
    C(
        "ck_van_don_loai_khop_doi_tra",
        "van_don",
        [{"loai": "'tra_hang'", "yeu_cau_doi_tra_id": NULL}, {"loai": "'giao_hang'", "yeu_cau_doi_tra_id": "1"}],
        [{"loai": "'tra_hang'", "yeu_cau_doi_tra_id": "1"}, {"loai": "'giao_hang'", "yeu_cau_doi_tra_id": NULL}],
    ),
    C(
        "ck_khuyen_mai_ket_thuc_sau_bat_dau",
        "khuyen_mai",
        [{"ket_thuc": "now()"}, {"ket_thuc": "now() - interval '1 day'"}],
        [{"ket_thuc": "now() + interval '1 second'"}],
    ),
    C("ck_khuyen_mai_gia_tri_gt_0", "khuyen_mai", [{"gia_tri": "0"}, {"gia_tri": "-5"}], [{"gia_tri": "1"}]),
    C(
        "ck_khuyen_mai_phan_tram_le_100",
        "khuyen_mai",
        [{"loai_giam": "'phan_tram'", "gia_tri": "101"}],
        [{"loai_giam": "'phan_tram'", "gia_tri": "100"}, {"loai_giam": "'so_tien'", "gia_tri": "50000"}],
    ),
    C("ck_khuyen_mai_luot_moi_khach_ge_1", "khuyen_mai", [{"luot_moi_khach": "0"}], [{"luot_moi_khach": "1"}]),
    C(
        "ck_khuyen_mai_pham_vi_mot_trong_hai",
        "khuyen_mai_pham_vi",
        [{"danh_muc_id": "1", "san_pham_id": "1"}, {"danh_muc_id": NULL, "san_pham_id": NULL}],
        [{"danh_muc_id": NULL, "san_pham_id": "1"}, {"danh_muc_id": "1", "san_pham_id": NULL}],
    ),
    *[
        C(
            ten,
            bang,
            [{"khach_hang_id": NULL, "nhan_vien_id": NULL}, {"khach_hang_id": "1", "nhan_vien_id": "1"}],
            [{"khach_hang_id": "1", "nhan_vien_id": NULL}, {"khach_hang_id": NULL, "nhan_vien_id": "1"}],
        )
        for ten, bang in [
            ("ck_thong_bao_mot_nguoi_nhan", "thong_bao"),
            ("ck_phien_dang_nhap_mot_chu_so_huu", "phien_dang_nhap"),
        ]
    ],
    *[
        C(
            ten,
            bang,
            [{nguoi_lap: "1", "nguoi_duyet_id": "1"}],
            [{nguoi_lap: "1", "nguoi_duyet_id": "2"}, {nguoi_lap: "1", "nguoi_duyet_id": NULL}],
        )
        for ten, bang, nguoi_lap in [
            ("ck_phieu_dieu_chinh_khac_nguoi_lap", "phieu_dieu_chinh", "nguoi_lap_id"),
            ("ck_phieu_huy_khac_nguoi_lap", "phieu_huy", "nguoi_lap_id"),
            ("ck_phieu_xuat_tra_khac_nguoi_lap", "phieu_xuat_tra", "nhan_vien_id"),
        ]
    ],
    C("ck_danh_gia_so_sao_1_5", "danh_gia", [{"so_sao": "0"}, {"so_sao": "6"}], [{"so_sao": "1"}, {"so_sao": "5"}]),
    C(
        "ck_tuong_tac_hoat_chat_a_nho_hon_b",
        "tuong_tac_hoat_chat",
        [{"hoat_chat_a_id": "2", "hoat_chat_b_id": "1"}, {"hoat_chat_a_id": "1", "hoat_chat_b_id": "1"}],
        [{"hoat_chat_a_id": "1", "hoat_chat_b_id": "2"}],
    ),
    C(
        "ck_ct_yeu_cau_don_thuoc_do_tin_cay_0_1",
        "ct_yeu_cau_don_thuoc",
        [{"do_tin_cay_ai": "1.01"}, {"do_tin_cay_ai": "-0.01"}],
        [{"do_tin_cay_ai": "0"}, {"do_tin_cay_ai": "1"}, {"do_tin_cay_ai": NULL}],
    ),
    C(
        "ck_de_xuat_nhap_hang_ky_hop_le",
        "de_xuat_nhap_hang",
        [
            {"ky_bat_dau": "DATE '2026-01-01'", "ky_ket_thuc": "DATE '2026-01-01'"},
            {"ky_bat_dau": "DATE '2026-02-01'", "ky_ket_thuc": "DATE '2026-01-01'"},
        ],
        [{"ky_bat_dau": "DATE '2026-01-01'", "ky_ket_thuc": "DATE '2026-01-02'"}],
    ),
    C(
        "ck_de_xuat_nhap_hang_de_xuat_ge_0",
        "de_xuat_nhap_hang",
        [{"so_luong_de_xuat": "-1"}],
        [{"so_luong_de_xuat": "0"}],
    ),
]


@pytest.mark.parametrize(("ten", "bang", "vi_pham", "hop_le"), CAC_CHECK)
async def test_check_tu_choi_du_lieu_sai_va_nhan_du_lieu_dung(engine_migration, ten, bang, vi_pham, hop_le):
    conn = await mo_ket_noi_thu(engine_migration)
    try:
        nen = await dong_nen(conn, bang)
        for dong in hop_le:
            assert await thu_chen(conn, bang, {**nen, **dong}) is None, f"{ten}: dòng hợp lệ {dong} bị từ chối"
        # Trên bảng đủ ràng buộc, dòng sai bị từ chối bởi một CHECK.
        for dong in vi_pham:
            ket_qua = await thu_chen(conn, bang, {**nen, **dong})
            assert ket_qua is not None and ket_qua[0] == CHECK_VIOLATION, f"{ten}: dòng sai {dong} lọt qua"
        # Gỡ các CHECK khác để chứng minh chính ràng buộc này là thứ từ chối (không phải ràng buộc bên cạnh).
        await go_check_khac(conn, bang, ten)
        for dong in vi_pham:
            assert await thu_chen(conn, bang, {**nen, **dong}) == (CHECK_VIOLATION, ten), f"{ten}: dòng sai {dong}"
        for dong in hop_le:
            assert await thu_chen(conn, bang, {**nen, **dong}) is None
    finally:
        await conn.close()


async def test_moi_check_trong_db_deu_co_test(engine_migration):
    """Thêm CHECK mới ở migration mà quên viết case ở trên sẽ làm test này fail."""
    async with engine_migration.connect() as conn:
        trong_db = set(
            (
                await conn.execute(
                    text(
                        "SELECT conname FROM pg_constraint WHERE contype = 'c' AND conrelid <> 0"
                    )  # bỏ CHECK của domain
                )
            ).scalars()
        )
    da_test = {p.values[0] for p in CAC_CHECK}
    assert len(trong_db) == 42
    assert trong_db == da_test


# --- Partial unique -------------------------------------------------------------------------------------------------

DIA_CHI = {
    "dia_chi_chi_tiet": "'1 Lê Lợi'",
    "ma_phuong_xa": "'1'",
    "ma_tinh": "'79'",
    "so_dien_thoai": "'0900000000'",
    "ten_nguoi_nhan": "'A'",
}


def U(ten: str, bang: str, dong_1: dict, vi_pham: dict, hop_le: list[dict]):
    """Dòng 1 chèn trước; `vi_pham` (áp lên dòng 1) chèn sau phải trùng khóa; các `hop_le` chèn sau phải được nhận."""
    return pytest.param(ten, bang, dong_1, vi_pham, hop_le, id=ten)


CAC_PARTIAL_UNIQUE = [
    U(
        "dia_chi_mot_mac_dinh",
        "dia_chi",
        {**DIA_CHI, "khach_hang_id": "1", "la_mac_dinh": "true"},
        {},
        [{"la_mac_dinh": "false"}, {"khach_hang_id": "2"}],
    ),
    U(
        "don_vi_mot_co_so",
        "don_vi_quy_doi",
        {"san_pham_id": "1", "ten_don_vi": "'Viên'", "he_so": "1"},
        {"ten_don_vi": "'Hộp'", "he_so": "1"},
        [{"ten_don_vi": "'Hộp'", "he_so": "10"}, {"ten_don_vi": "'Hộp'", "san_pham_id": "2"}],
    ),
    U(
        "don_vi_mot_mac_dinh",
        "don_vi_quy_doi",
        {"san_pham_id": "1", "ten_don_vi": "'Hộp'", "he_so": "10", "la_mac_dinh": "true"},
        {"ten_don_vi": "'Vỉ'", "he_so": "5"},
        [
            {"ten_don_vi": "'Vỉ'", "he_so": "5", "la_mac_dinh": "false"},
            {"ten_don_vi": "'Vỉ'", "he_so": "5", "san_pham_id": "2"},
        ],
    ),
    U(
        "anh_mot_anh_chinh",
        "anh_san_pham",
        {"san_pham_id": "1", "url": "'a.jpg'", "la_anh_chinh": "true"},
        {"url": "'b.jpg'"},
        [{"url": "'b.jpg'", "la_anh_chinh": "false"}, {"url": "'b.jpg'", "san_pham_id": "2"}],
    ),
    U(
        "don_thuoc_mot_don_mo",
        "don_hang",
        {"ma_don": "'DH1'", "yeu_cau_don_thuoc_id": "5"},
        {"ma_don": "'DH2'"},
        [
            {"ma_don": "'DH2'", "yeu_cau_don_thuoc_id": "6"},
            {"ma_don": "'DH2'", "yeu_cau_don_thuoc_id": NULL},
        ],
    ),
]


@pytest.mark.parametrize(("ten", "bang", "dong_1", "vi_pham", "hop_le"), CAC_PARTIAL_UNIQUE)
async def test_partial_unique_tu_choi_dong_trung_khoa(engine_migration, ten, bang, dong_1, vi_pham, hop_le):
    conn = await mo_ket_noi_thu(engine_migration)
    try:
        nen = await dong_nen(conn, bang)
        dong_1 = {**nen, **dong_1}

        async def chen_hai_dong(dong_2):
            """Chèn dòng 1 thật (trong savepoint để dọn), rồi thử dòng 2. Trả kết quả của dòng 2."""
            async with conn.begin_nested() as savepoint:
                assert await thu_chen_giu_lai(conn, bang, dong_1) is None
                ket_qua = await thu_chen(conn, bang, {**dong_1, **dong_2})
                await savepoint.rollback()
            return ket_qua

        assert await chen_hai_dong(vi_pham) == (UNIQUE_VIOLATION, ten)
        for dong in hop_le:
            assert await chen_hai_dong(dong) is None, f"{ten}: dòng hợp lệ {dong} bị từ chối"
    finally:
        await conn.close()


async def thu_chen_giu_lai(conn, bang: str, dong: dict[str, str]):
    """Như `thu_chen` nhưng giữ dòng lại trong transaction hiện tại nếu chèn được."""
    try:
        await conn.execute(text(f"INSERT INTO {bang} ({', '.join(dong)}) VALUES ({', '.join(dong.values())})"))
    except DBAPIError as loi:
        goc = loi.orig.__cause__ or loi.orig
        return goc.sqlstate, goc.constraint_name
    return None


async def test_don_thuoc_da_huy_thi_duoc_dung_lai_yeu_cau_don_thuoc(engine_migration):
    """Đơn đã hủy không chiếm chỗ: được tạo đơn mới từ cùng yêu cầu đơn thuốc (spec 02 mục 4.3)."""
    conn = await mo_ket_noi_thu(engine_migration)
    try:
        nen = await dong_nen(conn, "don_hang")
        cu = {**nen, "ma_don": "'DH1'", "yeu_cau_don_thuoc_id": "5", "trang_thai": "'da_huy'"}
        assert await thu_chen_giu_lai(conn, "don_hang", cu) is None
        assert (
            await thu_chen_giu_lai(conn, "don_hang", {**cu, "ma_don": "'DH2'", "trang_thai": "'cho_khach_xac_nhan'"})
            is None
        )
        # Giờ đã có một đơn mở: đơn mở thứ hai bị chặn.
        ket_qua = await thu_chen_giu_lai(
            conn, "don_hang", {**cu, "ma_don": "'DH3'", "trang_thai": "'cho_xac_nhan'", "phuong_thuc_tt": "'cod'"}
        )
        assert ket_qua == (UNIQUE_VIOLATION, "don_thuoc_mot_don_mo")
    finally:
        await conn.close()


# --- Hàm, sequence, index tìm kiếm ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("vao", "ra"),
    [
        ("Bổ phế", "Bo phe"),
        ("Đau đầu", "Dau dau"),
        ("Thuốc ho Bổ Phế", "Thuoc ho Bo Phe"),
        ("Paracetamol 500mg", "Paracetamol 500mg"),
    ],
)
async def test_f_unaccent_bo_dau_tieng_viet(engine_migration, vao, ra):
    async with engine_migration.connect() as conn:
        assert (await conn.execute(text("SELECT f_unaccent(:v)"), {"v": vao})).scalar_one() == ra


async def test_f_unaccent_la_immutable_va_null_an_toan(engine_migration):
    async with engine_migration.connect() as conn:
        dong = (
            await conn.execute(text("SELECT provolatile::text, proisstrict FROM pg_proc WHERE proname = 'f_unaccent'"))
        ).one()
        assert tuple(dong) == ("i", True)  # IMMUTABLE bắt buộc để dùng trong index biểu thức
        assert (await conn.execute(text("SELECT f_unaccent(NULL)"))).scalar_one() is None


@pytest.mark.parametrize(
    "ten_seq",
    [
        "seq_phieu_nhap",
        "seq_phieu_kiem_ke",
        "seq_phieu_dieu_chinh",
        "seq_phieu_huy",
        "seq_phieu_xuat_tra",
        "seq_lenh_thu_hoi",
        "seq_nhan_vien",
    ],
)
async def test_sequence_ma_chung_tu_tang_dan_tu_1(engine_migration, ten_seq):
    async with engine_migration.connect() as conn:
        a = (await conn.execute(text(f"SELECT nextval('{ten_seq}')"))).scalar_one()
        b = (await conn.execute(text(f"SELECT nextval('{ten_seq}')"))).scalar_one()
        assert b == a + 1
    # Chỉ kiểm tra tăng dần; không so với 1 vì các test khác trong cùng module có thể đã lấy số.


async def test_index_tim_kiem_duoc_planner_dung_khi_viet_dung_bieu_thuc(engine_migration):
    """Spec 02 mục 4.1: phải dùng đúng biểu thức f_unaccent(lower(...)) thì GIN trgm mới được dùng."""
    vector_0_1 = "[" + ",".join(["0.1"] * 1024) + "]"
    truy_van = {
        "san_pham_ten_trgm": "SELECT id FROM san_pham WHERE f_unaccent(lower('bo phe')) <% f_unaccent(lower(ten))",
        "hoat_chat_ten_trgm": "SELECT id FROM hoat_chat WHERE f_unaccent(lower('para')) <% f_unaccent(lower(ten))",
        "hoat_chat_khac_trgm": (
            "SELECT id FROM hoat_chat WHERE f_unaccent(lower('para')) <% f_unaccent(lower(coalesce(ten_khac, '')))"
        ),
        "tai_lieu_tri_thuc_hnsw": f"SELECT id FROM tai_lieu_tri_thuc ORDER BY embedding <=> '{vector_0_1}' LIMIT 5",
        "lich_su_tim_kiem_rong": "SELECT created_at FROM lich_su_tim_kiem WHERE so_ket_qua = 0 ORDER BY created_at",
    }
    async with engine_migration.connect() as conn:
        await conn.execute(text("SET LOCAL enable_seqscan = off"))  # bảng rỗng: ép planner chọn index nếu dùng được
        for ten_index, sql in truy_van.items():
            ke_hoach = "\n".join((await conn.execute(text(f"EXPLAIN {sql}"))).scalars())
            assert ten_index in ke_hoach, f"{ten_index} không được dùng:\n{ke_hoach}"
