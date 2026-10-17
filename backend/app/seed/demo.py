"""Dữ liệu demo (`python -m app.seed --demo`): đơn hàng nhiều trạng thái và khoảng 3 tháng doanh thu.

Mọi đơn đi qua API thật (bán tại quầy, đặt hàng COD, xác nhận, soạn, đóng gói, webhook vận chuyển giả) trong một
ứng dụng ASGI chạy cùng tiến trình, nên tồn kho, thẻ kho, giá vốn và lịch sử trạng thái đều do đúng mã nghiệp vụ ghi.
Sau đó mốc thời gian của từng đơn được dời về quá khứ (mọi cột `timestamptz` của đơn và các bản ghi con dời cùng một
độ lệch nên thứ tự các bước giữ nguyên). Cần `--mau` đã chạy trước; chạy lại khi đã có đơn thì bỏ qua.
"""

import hashlib
import io
import logging
import random
import uuid
from datetime import timedelta
from decimal import Decimal

import httpx
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang
from app.models.enums import LoaiSanPham, TrangThaiKinhDoanh, TrangThaiLo
from app.models.khach_hang import DiaChi, KhachHang
from app.models.kho import LoThuoc
from app.models.san_pham import AnhSanPham, DonViQuyDoi, SanPham
from app.modules.ban_hang.tu_hoan_tat import tu_hoan_tat_don
from app.seed.du_lieu_mau import MAT_KHAU_MAU

SO_NGAY_LICH_SU = 90
SO_NGAY_NHAP_LUI = 100
BASE = "/api/v1"
SDT_KHACH = ("0900000001", "0900000002")
LOAI_CT_DON = "don_hang"
BANG_THEO_DON = (
    ("don_hang", "id"),
    ("lich_su_trang_thai", "don_hang_id"),
    ("thanh_toan", "don_hang_id"),
    ("van_don", "don_hang_id"),
)


class LoiDemo(Exception):
    pass


async def _cot_thoi_gian(db: AsyncSession, bang: str) -> list[str]:
    return list(
        (
            await db.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :b AND data_type = 'timestamp with time zone'"
                ),
                {"b": bang},
            )
        ).scalars()
    )


async def _doi_moc(db: AsyncSession, don_id: int, luc_moi) -> None:
    """Dời mọi mốc thời gian của đơn và bản ghi con sao cho đơn được tạo lúc `luc_moi`."""
    cu = await db.scalar(select(DonHang.created_at).where(DonHang.id == don_id))
    do_lech = cu - luc_moi
    ct_ids = "SELECT id FROM ct_don_hang WHERE don_hang_id = :d"
    phan = [(b, f"{k} = :d") for b, k in BANG_THEO_DON]
    phan.append(("phan_bo_lo", f"ct_don_hang_id IN ({ct_ids})"))
    phan.append(("bien_dong_kho", f"chung_tu_loai = '{LOAI_CT_DON}' AND chung_tu_id = :d"))
    for bang, dieu_kien in phan:
        cot = await _cot_thoi_gian(db, bang)
        if not cot:
            continue
        dat = ", ".join(f"{c} = {c} - CAST(:lech AS interval)" for c in cot)
        await db.execute(text(f"UPDATE {bang} SET {dat} WHERE {dieu_kien}"), {"d": don_id, "lech": do_lech})
    await db.commit()


async def _doi_moc_nhap_kho(db: AsyncSession) -> None:
    """Phiếu nhập mẫu lùi về trước kỳ lịch sử để báo cáo nhập-xuất-tồn không có tồn đầu âm."""
    dich = bay_gio_utc() - timedelta(days=SO_NGAY_NHAP_LUI)
    for bang, dieu_kien in (
        ("phieu_nhap", "true"),
        ("bien_dong_kho", "chung_tu_loai = 'phieu_nhap'"),
        ("lo_thuoc", "true"),
    ):
        cot = await _cot_thoi_gian(db, bang)
        dat = ", ".join(f"{c} = LEAST({c}, :dich)" for c in cot)
        await db.execute(text(f"UPDATE {bang} SET {dat} WHERE {dieu_kien}"), {"dich": dich})
    await db.commit()


async def _dang_nhap(client: httpx.AsyncClient, url: str, than: dict) -> None:
    r = await client.post(f"{BASE}{url}", json=than)
    if r.status_code != 200:
        raise LoiDemo(f"Đăng nhập {url} thất bại ({r.status_code}): chạy `--mau` trước và không đổi mật khẩu mẫu")
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


async def _san_pham_ban_duoc(db: AsyncSession) -> list[tuple[int, int, Decimal]]:
    """(sản phẩm, đơn vị mặc định, giá) của sản phẩm bán tự do còn tồn: không kê đơn."""
    ton = (
        select(LoThuoc.san_pham_id, func.sum(LoThuoc.so_luong_ton - LoThuoc.so_luong_giu).label("t"))
        .where(LoThuoc.trang_thai == TrangThaiLo.dang_ban)
        .group_by(LoThuoc.san_pham_id)
        .subquery()
    )
    dong = (
        await db.execute(
            select(SanPham.id, DonViQuyDoi.id, DonViQuyDoi.gia_ban)
            .join(DonViQuyDoi, (DonViQuyDoi.san_pham_id == SanPham.id) & DonViQuyDoi.la_mac_dinh)
            .join(ton, ton.c.san_pham_id == SanPham.id)
            .where(
                SanPham.deleted_at.is_(None),
                SanPham.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh,
                SanPham.loai_san_pham != LoaiSanPham.thuoc_ke_don,
                ton.c.t >= 200,
            )
            .order_by(SanPham.id)
        )
    ).all()
    return [(a, b, c) for a, b, c in dong]


def _ve_anh_san_pham(ten: str) -> bytes:
    """Ảnh minh họa 600x600: nền chuyển màu theo tên, chữ cái đầu và tên sản phẩm (không dùng ảnh thương hiệu thật)."""
    h = hashlib.sha256(ten.encode()).digest()
    mau = tuple(90 + b % 120 for b in h[:3])
    anh = Image.new("RGB", (600, 600), mau)
    ve = ImageDraw.Draw(anh)
    for y in range(600):  # chuyển sáng dần xuống dưới
        sang = int(60 * y / 600)
        ve.line([(0, y), (600, y)], fill=tuple(min(255, c + sang) for c in mau))
    ve.ellipse([130, 90, 470, 430], fill=(255, 255, 255))
    try:
        to = ImageFont.truetype("DejaVuSans-Bold.ttf", 180)
        nho = ImageFont.truetype("DejaVuSans.ttf", 34)
    except OSError:
        to = nho = ImageFont.load_default()
    ve.text((300, 260), ten[:1].upper(), font=to, fill=mau, anchor="mm")
    dong, hien = "", []
    for tu in ten.split():
        if len(dong) + len(tu) > 22:
            hien.append(dong)
            dong = tu
        else:
            dong = f"{dong} {tu}".strip()
    hien.append(dong)
    for i, d in enumerate(hien[:2]):
        ve.text((300, 480 + 42 * i), d, font=nho, fill=(255, 255, 255), anchor="mm")
    ra = io.BytesIO()
    anh.save(ra, format="JPEG", quality=85)
    return ra.getvalue()


async def _nap_anh_san_pham(db: AsyncSession) -> int:
    """Mỗi sản phẩm chưa có ảnh nhận một ảnh minh họa (lưu qua lớp lưu trữ như ảnh tải lên thật)."""
    chua_co = (
        await db.execute(
            select(SanPham.id, SanPham.ten).where(
                ~select(AnhSanPham.id).where(AnhSanPham.san_pham_id == SanPham.id).exists(),
                SanPham.deleted_at.is_(None),
            )
        )
    ).all()
    for sp_id, ten in chua_co:
        khoa = await luu_tru.luu_tru().luu("san-pham", _ve_anh_san_pham(ten), "image/jpeg")
        db.add(AnhSanPham(san_pham_id=sp_id, url=luu_tru.url_cong_khai(khoa), thu_tu=0, la_anh_chinh=True))
    await db.commit()
    return len(chua_co)


async def seed_demo(app, db: AsyncSession, *, hat_giong: int = 2026) -> dict[str, int]:
    """Nạp dữ liệu demo qua `app` (ASGI). `db` là phiên riêng để đọc và dời mốc thời gian; hàm tự commit từng bước."""
    if await db.scalar(select(func.count()).select_from(DonHang)):
        return {}
    dem_anh = await _nap_anh_san_pham(db)
    for ten in ("app.truy_cap", "httpx", "app.tich_hop.tin_nhan.gia"):
        logging.getLogger(ten).setLevel(logging.ERROR)  # hàng trăm yêu cầu nội bộ, không cần in
    rng = random.Random(hat_giong)
    sp = await _san_pham_ban_duoc(db)
    if len(sp) < 8:
        raise LoiDemo("Chưa có dữ liệu mẫu đủ tồn kho: chạy `python -m app.seed --mau` trước")
    khach_ids = {sdt: await db.scalar(select(KhachHang.id).where(KhachHang.so_dien_thoai == sdt)) for sdt in SDT_KHACH}
    hom_nay = bay_gio_utc()
    dem = {"anh_san_pham": dem_anh, "don_quay": 0, "don_online": 0, "don_dang_xu_ly": 0}
    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://demo") as ds,
        httpx.AsyncClient(transport=transport, base_url="http://demo") as kho,
        httpx.AsyncClient(transport=transport, base_url="http://demo") as ngoai,
        httpx.AsyncClient(transport=transport, base_url="http://demo") as k1,
        httpx.AsyncClient(transport=transport, base_url="http://demo") as k2,
    ):
        await _dang_nhap(ds, "/noi-bo/auth/dang-nhap", {"email": "duocsi@example.com", "mat_khau": MAT_KHAU_MAU})
        await _dang_nhap(kho, "/noi-bo/auth/dang-nhap", {"email": "kho@example.com", "mat_khau": MAT_KHAU_MAU})
        for c, sdt in ((k1, SDT_KHACH[0]), (k2, SDT_KHACH[1])):
            await _dang_nhap(c, "/auth/dang-nhap", {"ten_dang_nhap": sdt, "mat_khau": MAT_KHAU_MAU})

        async def ban_tai_quay(ngay_truoc: int) -> bool:
            dong = [
                {"san_pham_id": s, "don_vi_id": u, "so_luong": rng.randint(1, 3)}
                for s, u, _ in rng.sample(sp, rng.randint(1, 3))
            ]
            tien_mat = rng.random() < 0.7
            r = await ds.post(
                f"{BASE}/noi-bo/pos/don",
                json={
                    "dong": dong,
                    "phuong_thuc_thu": "tien_mat" if tien_mat else "chuyen_khoan",
                    **({"tien_khach_dua": "10000000"} if tien_mat else {}),
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
            if r.status_code not in (200, 201):
                if r.status_code not in (409, 422):  # hết hàng hoặc vượt số lượng tối đa của một sản phẩm: bỏ đơn này
                    raise LoiDemo(f"Bán tại quầy lỗi: {r.text}")
                return False
            luc = hom_nay - timedelta(days=ngay_truoc, hours=rng.randint(0, 9), minutes=rng.randint(0, 59))
            await _doi_moc(db, r.json()["don_id"], luc)
            return True

        async def dat_cod(khach: httpx.AsyncClient, khach_id: int) -> str:
            dia_chi = await db.scalar(select(DiaChi.id).where(DiaChi.khach_hang_id == khach_id).limit(1))
            for _ in range(20):
                await khach.delete(f"{BASE}/toi/gio-hang")
                da_them = 0
                for s, u, _ in rng.sample(sp, rng.randint(1, 3)):
                    for so_luong in (rng.randint(1, 3), 1):  # vượt số lượng tối đa mỗi đơn thì thử 1, không được thì bỏ
                        r = await khach.post(
                            f"{BASE}/toi/gio-hang/dong", json={"san_pham_id": s, "don_vi_id": u, "so_luong": so_luong}
                        )
                        if r.status_code == 200:
                            da_them += 1
                            break
                        if r.json().get("ma_loi") != "VUOT_SO_LUONG_TOI_DA":
                            raise LoiDemo(f"Thêm giỏ hàng lỗi: {r.text}")
                if not da_them:
                    continue
                than = {"hinh_thuc_nhan": "giao_tan_noi", "dia_chi_id": dia_chi, "phuong_thuc_tt": "cod"}
                r = await khach.post(f"{BASE}/toi/don-hang", json=than, headers={"Idempotency-Key": str(uuid.uuid4())})
                if r.status_code == 201:
                    return r.json()["ma_don"]
                if r.json().get("ma_loi") != "HET_HANG":  # hết hàng: thử giỏ khác
                    raise LoiDemo(f"Đặt hàng lỗi: {r.text}")
            raise LoiDemo("Không đặt được đơn demo: tồn kho các sản phẩm mẫu quá thấp")

        async def id_don(ma: str) -> int:
            return await db.scalar(select(DonHang.id).where(DonHang.ma_don == ma))

        async def xu_ly_den(ma: str, buoc: str) -> int:
            """Đưa đơn đến `buoc`: xac_nhan | dang_soan | cho_lay | dang_giao | da_giao | huy."""
            don_id = await id_don(ma)
            if buoc == "huy":
                r = await ds.post(f"{BASE}/noi-bo/don-hang/{don_id}/huy", json={"ly_do": "Khách đổi ý, gọi điện hủy"})
                if r.status_code != 200:
                    raise LoiDemo(f"Hủy đơn lỗi: {r.text}")
                return don_id
            thu_tu = ["xac_nhan", "dang_soan", "cho_lay", "dang_giao", "da_giao"]
            den = thu_tu.index(buoc)
            r = await ds.post(f"{BASE}/noi-bo/don-hang/{don_id}/xac-nhan")
            if r.status_code != 200:
                raise LoiDemo(f"Xác nhận đơn lỗi: {r.text}")
            if den >= 1:
                await kho.post(f"{BASE}/noi-bo/soan-hang/{don_id}/bat-dau")
            if den >= 2:
                await kho.post(f"{BASE}/noi-bo/soan-hang/{don_id}/dong-goi")
            if den >= 3:
                ma_vd = await db.scalar(text("SELECT ma_van_don FROM van_don WHERE don_hang_id = :d"), {"d": don_id})
                for tt in ("picked", "delivered")[: den - 2]:
                    r = await ngoai.post(
                        f"{BASE}/webhook/gia-van-chuyen", json={"ma_van_don": ma_vd, "trang_thai_doi_tac": tt}
                    )
                    if r.status_code != 200:
                        raise LoiDemo(f"Webhook vận chuyển lỗi: {r.text}")
            return don_id

        # 1. Lịch sử bán tại quầy: 90 ngày, ngày thường nhiều hơn, vài ngày nghỉ
        for ngay in range(SO_NGAY_LICH_SU, 0, -1):
            if rng.random() < 0.08:
                continue
            so_don = rng.randint(1, 4) if (hom_nay - timedelta(days=ngay)).weekday() < 5 else rng.randint(0, 2)
            for _ in range(so_don):
                if await ban_tai_quay(ngay):
                    dem["don_quay"] += 1

        # 2. Đơn online đã hoàn tất hoặc bị hủy trong quá khứ
        kh = ((k1, khach_ids[SDT_KHACH[0]]), (k2, khach_ids[SDT_KHACH[1]]))
        for i in range(24):
            c, kid = kh[i % 2]
            ma = await dat_cod(c, kid)
            buoc = "huy" if i % 8 == 7 else "da_giao"
            don_id = await xu_ly_den(ma, buoc)
            await _doi_moc(
                db, don_id, hom_nay - timedelta(days=rng.randint(10, SO_NGAY_LICH_SU - 5), hours=rng.randint(0, 8))
            )
            dem["don_online"] += 1

        # 3. Đơn đang xử lý: mỗi trạng thái một vài đơn, mốc thời gian là bây giờ
        for i, buoc in enumerate(("moi", "moi", "xac_nhan", "dang_soan", "cho_lay", "dang_giao", "da_giao", "huy")):
            c, kid = kh[i % 2]
            ma = await dat_cod(c, kid)
            if buoc != "moi":
                await xu_ly_den(ma, buoc)
            dem["don_dang_xu_ly"] += 1
        await _doi_moc_nhap_kho(db)
        await db.commit()
        # Đơn đã giao quá hạn đổi trả thì tự hoàn tất như job HT08 ngoài đời
        async with db.begin():
            ket_qua = await tu_hoan_tat_don(db)
        dem["don_hoan_tat_tu_dong"] = len(ket_qua.hoan_tat)
    return dem
