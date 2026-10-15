"""Mật khẩu (Argon2id, spec 06 mục 3) và access token JWT."""

import jwt
import pytest
from pydantic import SecretStr

from app.core.bao_mat import (
    bam_mat_khau,
    bam_mat_khau_async,
    giai_ma_access_token,
    khoa_hmac,
    kiem_tra_mat_khau,
    kiem_tra_mat_khau_async,
    mat_khau_du_manh,
    tao_access_token,
)
from app.core.config import settings


def test_bam_ra_argon2id_khong_chua_mat_khau_goc():
    ma_bam = bam_mat_khau("Abc12345")
    assert ma_bam.startswith("$argon2id$")
    assert "Abc12345" not in ma_bam


def test_hai_lan_bam_cung_mat_khau_cho_ket_qua_khac_nhau_vi_co_salt():
    assert bam_mat_khau("Abc12345") != bam_mat_khau("Abc12345")


def test_kiem_tra_dung_va_sai():
    ma_bam = bam_mat_khau("Abc12345")
    assert kiem_tra_mat_khau("Abc12345", ma_bam) is True
    assert kiem_tra_mat_khau("abc12345", ma_bam) is False
    assert kiem_tra_mat_khau("", ma_bam) is False


@pytest.mark.parametrize("ma_bam", ["", "khong-phai-ma-bam", "$argon2id$hong", "x" * 300])
def test_ma_bam_hong_tra_false_khong_nem_loi(ma_bam):
    assert kiem_tra_mat_khau("Abc12345", ma_bam) is False


def test_mat_khau_tieng_viet_co_dau_bam_va_kiem_tra_duoc():
    ma_bam = bam_mat_khau("Mậtkhẩu123")
    assert kiem_tra_mat_khau("Mậtkhẩu123", ma_bam) is True
    assert kiem_tra_mat_khau("Matkhau123", ma_bam) is False


@pytest.mark.parametrize(
    ("mat_khau", "du_manh"),
    [
        ("abc12345", True),
        ("Mậtkhẩu123", True),
        ("a1b2c3d4", True),
        ("doi-mat-khau-nay-123", True),
        ("abc1234", False),  # 7 ký tự
        ("abcdefgh", False),  # không có số
        ("12345678", False),  # không có chữ
        ("        1a", True),  # đủ 8 ký tự, có chữ và số (dấu cách vẫn tính ký tự)
        ("", False),
    ],
)
def test_mat_khau_du_manh(mat_khau, du_manh):
    assert mat_khau_du_manh(mat_khau) is du_manh


# --- Access token JWT (spec 06 mục 3) -------------------------------------------------------------------------------


@pytest.fixture
def khoa_jwt(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", SecretStr("khoa-thu-nghiem-" + "x" * 32))


def test_token_co_du_claim_theo_spec(khoa_jwt):
    token = tao_access_token(42, "khach")
    claim = jwt.decode(token, options={"verify_signature": False})
    assert set(claim) == {"sub", "aud", "exp", "iat", "jti"}
    assert claim["sub"] == "42" and claim["aud"] == "khach"
    assert claim["exp"] - claim["iat"] == 15 * 60
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


def test_giai_ma_dung_aud_tra_ve_claim(khoa_jwt):
    claim = giai_ma_access_token(tao_access_token(7, "noi_bo"), "noi_bo")
    assert claim["sub"] == "7"


def test_khach_va_noi_bo_khong_dung_chung_token(khoa_jwt):
    with pytest.raises(jwt.InvalidAudienceError):
        giai_ma_access_token(tao_access_token(1, "khach"), "noi_bo")
    with pytest.raises(jwt.InvalidAudienceError):
        giai_ma_access_token(tao_access_token(1, "noi_bo"), "khach")


def test_aud_la_bi_tu_choi_khi_tao(khoa_jwt):
    with pytest.raises(ValueError, match="aud"):
        tao_access_token(1, "admin")


def test_token_het_han(khoa_jwt):
    with pytest.raises(jwt.ExpiredSignatureError):
        giai_ma_access_token(tao_access_token(1, "khach", het_han_phut=-1), "khach")


def test_token_bi_sua_hoac_sai_khoa_bi_tu_choi(khoa_jwt, monkeypatch):
    token = tao_access_token(1, "khach")
    with pytest.raises(jwt.InvalidTokenError):
        giai_ma_access_token(token[:-2] + ("AA" if not token.endswith("AA") else "BB"), "khach")
    monkeypatch.setattr(settings, "JWT_SECRET", SecretStr("khoa-khac-" + "y" * 40))
    with pytest.raises(jwt.InvalidSignatureError):
        giai_ma_access_token(token, "khach")


def test_token_khong_ky_alg_none_bi_tu_choi(khoa_jwt):
    gia = jwt.encode({"sub": "1", "aud": "khach", "exp": 9999999999, "jti": "x"}, key=None, algorithm="none")
    with pytest.raises(jwt.InvalidTokenError):
        giai_ma_access_token(gia, "khach")


def test_moi_token_co_jti_rieng(khoa_jwt):
    jti = {jwt.decode(tao_access_token(1, "khach"), options={"verify_signature": False})["jti"] for _ in range(20)}
    assert len(jti) == 20


@pytest.mark.parametrize("khoa", ["", "ngan"])
def test_khong_co_khoa_hoac_khoa_ngan_thi_tu_choi_tao_token(monkeypatch, khoa):
    monkeypatch.setattr(settings, "JWT_SECRET", SecretStr(khoa))
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        tao_access_token(1, "khach")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        giai_ma_access_token("a.b.c", "khach")


def test_khoa_jwt_con_la_gia_tri_mau_cua_env_example_bi_tu_choi(monkeypatch):
    mau = "doi-gia-tri-nay-thanh-chuoi-ngau-nhien-it-nhat-32-ky-tu"
    assert len(mau) >= 32  # dài đủ, nhưng là giá trị công khai trong repo
    monkeypatch.setattr(settings, "JWT_SECRET", SecretStr(mau))
    with pytest.raises(RuntimeError, match="giá trị mẫu"):
        tao_access_token(1, "khach")


def test_khoa_hmac_xac_dinh_tach_theo_muc_dich_va_phu_thuoc_khoa_goc(khoa_jwt, monkeypatch):
    otp = khoa_hmac("otp")
    assert otp == khoa_hmac("otp") and len(otp) == 32
    assert khoa_hmac("khac") != otp  # mỗi mục đích một khóa con, lộ một khóa không lộ khóa gốc hay khóa khác
    assert otp != settings.JWT_SECRET.get_secret_value().encode()
    monkeypatch.setattr(settings, "JWT_SECRET", SecretStr("khoa-khac-" + "y" * 40))
    assert khoa_hmac("otp") != otp


def test_khoa_hmac_cung_tu_choi_khoa_goc_thieu_hoac_mau(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", SecretStr(""))
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        khoa_hmac("otp")


async def test_bam_va_kiem_tra_mat_khau_khong_chan_vong_lap_su_kien():
    ma_bam = await bam_mat_khau_async("Abc12345")
    assert ma_bam.startswith("$argon2id$")
    assert await kiem_tra_mat_khau_async("Abc12345", ma_bam) is True
    assert await kiem_tra_mat_khau_async("sai", ma_bam) is False
