"""KVL09: đăng ký khách hàng bằng SĐT + OTP (POST /api/v1/auth/dang-ky)."""

import asyncio
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select, text

from app.core.bao_mat import kiem_tra_mat_khau
from app.core.db import get_engine
from app.core.gioi_han import lay_bo_gioi_han_otp
from app.main import create_app
from app.models.khach_hang import KhachHang, MaOtp
from app.modules.tai_khoan.otp import bam_otp
from app.tich_hop.tin_nhan import lay_kenh_tin_nhan
from tests.factories import tao_khach

SDT = "0912345678"
MAT_KHAU = "Matkhau123"


async def xin_otp(client, so_dien_thoai=SDT):
    r = await client.post("/api/v1/auth/otp", json={"so_dien_thoai": so_dien_thoai, "muc_dich": "dang_ky"})
    assert r.status_code == 200
    return r


def du_lieu(ma_otp: str, **ghi_de):
    return {
        "so_dien_thoai": SDT,
        "otp": ma_otp,
        "mat_khau": MAT_KHAU,
        "ho_ten": "Nguyễn Văn A",
        "email": "Nguyen.Van.A@Example.com",
        "dong_y_chinh_sach": True,
    } | ghi_de


async def dang_ky(client, ma_otp, **ghi_de):
    return await client.post("/api/v1/auth/dang-ky", json=du_lieu(ma_otp, **ghi_de))


async def so_khach(db) -> int:
    return (await db.execute(select(func.count()).select_from(KhachHang))).scalar_one()


async def otp_hien_tai(db) -> MaOtp:
    return (await db.execute(select(MaOtp).where(MaOtp.dich_den == SDT).order_by(MaOtp.id.desc()))).scalars().first()


async def test_dang_ky_thanh_cong(client, db, kenh_tin_nhan, thoi_gian):
    await xin_otp(client)
    phan_hoi = await dang_ky(client, kenh_tin_nhan.ma_otp_cuoi())
    assert phan_hoi.status_code == 201
    body = phan_hoi.json()
    assert set(body) == {"id", "ho_ten", "so_dien_thoai", "email"}  # không trả hash, token hay trạng thái nội bộ
    assert (body["ho_ten"], body["so_dien_thoai"], body["email"]) == ("Nguyễn Văn A", SDT, "nguyen.van.a@example.com")

    khach = (await db.execute(select(KhachHang).where(KhachHang.id == body["id"]))).scalar_one()
    assert kiem_tra_mat_khau(MAT_KHAU, khach.mat_khau_hash) and khach.mat_khau_hash.startswith("$argon2id$")
    assert MAT_KHAU not in phan_hoi.text
    assert khach.trang_thai == "hoat_dong" and khach.so_lan_dang_nhap_sai == 0 and khach.khoa_den is None
    assert abs((khach.dong_y_chinh_sach_luc - thoi_gian.bay_gio).total_seconds()) < 5  # lưu thời điểm đồng ý chính sách
    assert (await otp_hien_tai(db)).da_dung is True


async def test_so_dien_thoai_dang_ky_duoc_chuan_hoa(client, db, kenh_tin_nhan):
    await xin_otp(client, SDT)
    phan_hoi = await dang_ky(client, kenh_tin_nhan.ma_otp_cuoi(), so_dien_thoai="+84 912-345-678")
    assert phan_hoi.status_code == 201 and phan_hoi.json()["so_dien_thoai"] == SDT


@pytest.mark.parametrize("email", [None, "", "   "])
async def test_email_la_tuy_chon(client, db, kenh_tin_nhan, email):
    await xin_otp(client)
    phan_hoi = await dang_ky(client, kenh_tin_nhan.ma_otp_cuoi(), email=email)
    assert phan_hoi.status_code == 201 and phan_hoi.json()["email"] is None


async def test_ho_ten_duoc_cat_khoang_trang(client, kenh_tin_nhan):
    await xin_otp(client)
    phan_hoi = await dang_ky(client, kenh_tin_nhan.ma_otp_cuoi(), ho_ten="  Lê Thị B  ")
    assert phan_hoi.json()["ho_ten"] == "Lê Thị B"


async def test_otp_chi_dung_duoc_mot_lan(client, db, kenh_tin_nhan):
    await xin_otp(client)
    ma = kenh_tin_nhan.ma_otp_cuoi()
    assert (await dang_ky(client, ma)).status_code == 201
    lai = await dang_ky(client, ma, email="khac@example.com")
    assert lai.status_code == 422 and lai.json()["ma_loi"] == "OTP_SAI"
    assert await so_khach(db) == 1


# --- OTP sai, hết hạn, quá số lần ---------------------------------------------------------------------------------------


async def test_otp_sai_tra_422_khong_tao_khach_va_dem_so_lan_con_lai(client, db, kenh_tin_nhan):
    await xin_otp(client)
    ma_dung = kenh_tin_nhan.ma_otp_cuoi()
    ma_sai = "000000" if ma_dung != "000000" else "111111"
    phan_hoi = await dang_ky(client, ma_sai)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["ma_loi"] == "OTP_SAI"
    assert phan_hoi.json()["chi_tiet"] == {"so_lan_con_lai": 4}
    assert await so_khach(db) == 0
    assert (await otp_hien_tai(db)).so_lan_thu == 1  # lần sai được lưu dù request trả lỗi


async def test_sai_5_lan_thi_ma_dung_cung_bi_tu_choi(client, db, kenh_tin_nhan):
    """Chặn dò mã: đếm lần thử phải được commit dù mỗi lần request đều trả lỗi."""
    await xin_otp(client)
    ma_dung = kenh_tin_nhan.ma_otp_cuoi()
    ma_sai = "000000" if ma_dung != "000000" else "111111"
    con_lai = [(await dang_ky(client, ma_sai)).json()["chi_tiet"]["so_lan_con_lai"] for _ in range(5)]
    assert con_lai == [4, 3, 2, 1, 0]
    sau = await dang_ky(client, ma_dung)  # đúng mã nhưng đã hết lượt thử
    assert sau.status_code == 422 and sau.json()["ma_loi"] == "OTP_SAI"
    assert "xin mã mới" in sau.json()["thong_diep"].lower()
    assert await so_khach(db) == 0
    assert (await otp_hien_tai(db)).so_lan_thu == 5  # không đếm thêm khi đã khóa


async def test_xin_ma_moi_sau_khi_bi_khoa_thi_dang_ky_duoc(client, db, kenh_tin_nhan):
    await xin_otp(client)
    for _ in range(5):
        await dang_ky(client, "000000" if kenh_tin_nhan.ma_otp_cuoi() != "000000" else "111111")
    await xin_otp(client)
    assert (await dang_ky(client, kenh_tin_nhan.ma_otp_cuoi())).status_code == 201


async def test_otp_het_han_sau_5_phut(client, db, kenh_tin_nhan, thoi_gian):
    await xin_otp(client)
    ma = kenh_tin_nhan.ma_otp_cuoi()
    thoi_gian.tien(minutes=4, seconds=59)
    # Còn hạn (chưa đủ 5 phút): kiểm tra mà không dùng, để mô phỏng lần thử sai không ảnh hưởng hạn
    thoi_gian.tien(seconds=2)
    phan_hoi = await dang_ky(client, ma)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["ma_loi"] == "OTP_HET_HAN"
    assert await so_khach(db) == 0


async def test_otp_con_han_den_giay_cuoi(client, db, kenh_tin_nhan, thoi_gian):
    await xin_otp(client)
    thoi_gian.tien(minutes=4, seconds=59)
    assert (await dang_ky(client, kenh_tin_nhan.ma_otp_cuoi())).status_code == 201


async def test_otp_het_han_khong_bi_tinh_la_lan_thu(client, db, kenh_tin_nhan, thoi_gian):
    await xin_otp(client)
    thoi_gian.tien(minutes=6)
    await dang_ky(client, kenh_tin_nhan.ma_otp_cuoi())
    assert (await otp_hien_tai(db)).so_lan_thu == 0


async def test_chua_xin_otp_thi_tra_otp_sai_giong_het_truong_hop_sai(client, db):
    phan_hoi = await dang_ky(client, "123456")
    assert phan_hoi.status_code == 422 and phan_hoi.json()["ma_loi"] == "OTP_SAI"
    assert "chi_tiet" in phan_hoi.json()


async def test_otp_cua_so_khac_khong_dung_duoc(client, db, kenh_tin_nhan):
    await xin_otp(client, "0911111111")
    ma_cua_so_khac = kenh_tin_nhan.ma_otp_cuoi()
    phan_hoi = await dang_ky(client, ma_cua_so_khac, so_dien_thoai=SDT)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["ma_loi"] == "OTP_SAI"


async def test_khong_do_ra_so_da_dang_ky_qua_cach_dem_lan_thu(client, db, kenh_tin_nhan):
    """Số đã đăng ký và số chưa đăng ký phải cho chuỗi phản hồi y hệt nhau khi đoán mã (spec 06 mục 3)."""
    await tao_khach(db, so_dien_thoai="0922222222")

    async def chuoi(so_dien_thoai):
        await xin_otp(client, so_dien_thoai)
        ma_that = kenh_tin_nhan.sms[-1][1]
        doan = "000000" if "000000" not in ma_that else "111111"
        return [
            (r.status_code, r.json())
            for r in [await dang_ky(client, doan, so_dien_thoai=so_dien_thoai, email=None) for _ in range(6)]
        ]

    assert await chuoi("0933333333") == await chuoi("0922222222")


# --- Trùng dữ liệu ------------------------------------------------------------------------------------------------------


async def tao_otp_hop_le(db, so_dien_thoai, ma, thoi_gian):
    db.add(
        MaOtp(
            dich_den=so_dien_thoai,
            ma_hash=bam_otp(so_dien_thoai, "dang_ky", ma),
            muc_dich="dang_ky",
            het_han=thoi_gian.bay_gio + timedelta(minutes=5),
            created_at=thoi_gian.bay_gio,
        )
    )
    await db.flush()


async def test_so_dien_thoai_da_co_tai_khoan_tra_409(client, db, thoi_gian):
    """Đường phòng thủ (đua giữa hai đăng ký, hoặc OTP dựng tay): API không bao giờ tạo hai khách cùng số."""
    await tao_khach(db, so_dien_thoai=SDT)
    await tao_otp_hop_le(db, SDT, "654321", thoi_gian)
    phan_hoi = await dang_ky(client, "654321")
    assert phan_hoi.status_code == 409 and phan_hoi.json()["ma_loi"] == "TRUNG_DU_LIEU"
    assert phan_hoi.json()["chi_tiet"] == {"truong": "so_dien_thoai"}
    assert await so_khach(db) == 1


async def test_email_da_dung_tra_409_khong_phan_biet_hoa_thuong(client, db, kenh_tin_nhan):
    await tao_khach(db, email="nguyen.van.a@example.com")
    await xin_otp(client)
    phan_hoi = await dang_ky(client, kenh_tin_nhan.ma_otp_cuoi(), email="NGUYEN.VAN.A@example.com")
    assert phan_hoi.status_code == 409 and phan_hoi.json()["chi_tiet"] == {"truong": "email"}
    assert await so_khach(db) == 1


async def test_loi_trung_email_khong_tieu_thu_otp(client, db, kenh_tin_nhan):
    """Người dùng sửa email rồi gửi lại với cùng OTP được, vì request lỗi đã rollback."""
    await tao_khach(db, email="nguyen.van.a@example.com")
    await xin_otp(client)
    ma = kenh_tin_nhan.ma_otp_cuoi()
    assert (await dang_ky(client, ma)).status_code == 409
    assert (await dang_ky(client, ma, email="khac@example.com")).status_code == 201


# --- Kiểm tra dữ liệu đầu vào -------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ghi_de", "truong"),
    [
        ({"mat_khau": "abc12"}, "mat_khau"),  # ngắn
        ({"mat_khau": "abcdefgh"}, "mat_khau"),  # không có số
        ({"mat_khau": "12345678"}, "mat_khau"),  # không có chữ
        ({"mat_khau": "a1" * 70}, "mat_khau"),  # quá dài (140)
        ({"ho_ten": ""}, "ho_ten"),
        ({"ho_ten": "   "}, "ho_ten"),
        ({"ho_ten": "A" * 151}, "ho_ten"),
        ({"email": "khong-phai-email"}, "email"),
        ({"email": "a@b"}, "email"),
        ({"email": "a" * 150 + "@example.com"}, "email"),
        ({"otp": "12345"}, "otp"),
        ({"otp": "1234567"}, "otp"),
        ({"otp": "12345a"}, "otp"),
        ({"dong_y_chinh_sach": False}, "dong_y_chinh_sach"),
        ({"so_dien_thoai": "0212345678"}, "so_dien_thoai"),
    ],
)
async def test_du_lieu_khong_hop_le_tra_400_dung_truong_va_khong_ton_luot_thu_otp(
    client, db, kenh_tin_nhan, ghi_de, truong
):
    await xin_otp(client)
    ma = kenh_tin_nhan.ma_otp_cuoi()
    phan_hoi = await dang_ky(client, ma, **ghi_de)
    assert phan_hoi.status_code == 400 and phan_hoi.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    assert truong in [e["truong"] for e in phan_hoi.json()["chi_tiet"]]
    assert await so_khach(db) == 0
    assert (await otp_hien_tai(db)).so_lan_thu == 0  # lỗi định dạng không làm hao OTP của người dùng
    assert (await dang_ky(client, ma)).status_code == 201  # sửa lại rồi gửi vẫn được


@pytest.mark.parametrize("thieu", ["so_dien_thoai", "otp", "mat_khau", "ho_ten", "dong_y_chinh_sach"])
async def test_thieu_truong_bat_buoc_tra_400(client, thieu):
    body = du_lieu("123456")
    del body[thieu]
    phan_hoi = await client.post("/api/v1/auth/dang-ky", json=body)
    assert phan_hoi.status_code == 400
    assert phan_hoi.json()["chi_tiet"] == [{"truong": thieu, "loi": "Bắt buộc nhập"}]


async def test_mat_khau_khong_xuat_hien_trong_log_va_loi(client, kenh_tin_nhan, bat_log):
    await xin_otp(client)
    await dang_ky(client, kenh_tin_nhan.ma_otp_cuoi(), mat_khau="a")  # sai định dạng
    await dang_ky(client, "000000")
    nhat_ky = str(bat_log())
    assert MAT_KHAU not in nhat_ky and "Matkhau" not in nhat_ky


# --- Đồng thời ----------------------------------------------------------------------------------------------------------


async def test_hai_dang_ky_dong_thoi_cung_otp_chi_mot_thanh_cong(engine_test, db_that, kenh_tin_nhan, gioi_han_ip):
    """Khóa dòng OTP: hai request cùng lúc không thể cùng xác thực một mã rồi cùng tạo tài khoản."""
    app = create_app()
    app.dependency_overrides[get_engine] = lambda: engine_test
    app.dependency_overrides[lay_kenh_tin_nhan] = lambda: kenh_tin_nhan
    app.dependency_overrides[lay_bo_gioi_han_otp] = lambda: gioi_han_ip
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        await xin_otp(c)
        ma = kenh_tin_nhan.ma_otp_cuoi()
        ket_qua = await asyncio.gather(dang_ky(c, ma, email="a@example.com"), dang_ky(c, ma, email="b@example.com"))
    assert sorted(r.status_code for r in ket_qua) == [201, 422]
    async with db_that() as s:
        assert (await s.execute(text("SELECT count(*) FROM khach_hang"))).scalar_one() == 1
