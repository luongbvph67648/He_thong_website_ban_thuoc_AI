"""AD10: đồng bộ kho tri thức AI (`tai_lieu_tri_thuc`) từ nội dung chuyên môn đã duyệt và bài viết (spec 07 mục 3).

Không commit. Chia đoạn theo trường, bỏ qua đoạn có `hash_noi_dung` và mô hình không đổi, xóa đoạn của nguồn không còn
hợp lệ. Giá và tồn kho không bao giờ đưa vào vector.
"""

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import embedding
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ai import TaiLieuTriThuc
from app.models.enums import (
    LoaiBaiViet,
    NguonTriThuc,
    TrangThaiKinhDoanh,
    TrangThaiNoiDung,
)
from app.models.he_thong import BaiViet
from app.models.san_pham import DanhMuc, HoatChat, SanPham, ThanhPhan, ThongTinChuyenMon

KICH_THUOC_DOAN = 800
CHONG_LAN = 100
LO_EMBED = 16
KHOA_TU_VAN = "ai_dong_bo_tri_thuc"
TRUONG_CHUYEN_MON = (
    "chi_dinh",
    "chong_chi_dinh",
    "lieu_dung_tham_khao",
    "tac_dung_phu",
    "than_trong",
    "tuong_tac_thuoc",
    "phu_nu_co_thai_cho_con_bu",
    "tre_em",
    "qua_lieu_xu_tri",
    "bao_quan",
)
NHAN_TRUONG = {
    "chi_dinh": "chỉ định",
    "chong_chi_dinh": "chống chỉ định",
    "lieu_dung_tham_khao": "liều dùng tham khảo",
    "tac_dung_phu": "tác dụng phụ",
    "than_trong": "thận trọng",
    "tuong_tac_thuoc": "tương tác thuốc",
    "phu_nu_co_thai_cho_con_bu": "phụ nữ có thai, cho con bú",
    "tre_em": "trẻ em",
    "qua_lieu_xu_tri": "quá liều và xử trí",
    "bao_quan": "bảo quản",
}
_DAU_CAU = re.compile(r"(?<=[.!?])\s+|\n+")


def _gt(x: Any) -> str:
    """Giá trị chuỗi của enum (đối tượng nạp sẵn trong phiên có thể còn giữ chuỗi thô)."""
    return x.value if isinstance(x, Enum) else str(x)


@dataclass
class Doan:
    nguon_loai: NguonTriThuc
    nguon_id: int
    truong: str
    so_doan: int
    noi_dung: str
    san_pham_id: int | None
    metadata: dict[str, Any]

    @property
    def khoa(self) -> tuple[str, int, str, int]:
        return (_gt(self.nguon_loai), self.nguon_id, self.truong, self.so_doan)

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.noi_dung.encode()).hexdigest()


class KetQuaDongBo(BaseModel):
    them: int = 0
    sua: int = 0
    xoa: int = 0
    bo_qua: int = 0
    tong_doan: int = 0
    mo_hinh: str = ""


def chia_doan(van_ban: str, kich_thuoc: int = KICH_THUOC_DOAN, chong_lan: int = CHONG_LAN) -> list[str]:
    """Cắt văn bản dài hơn `kich_thuoc` ký tự thành các đoạn chồng `chong_lan` ký tự; văn bản ngắn giữ nguyên."""
    van_ban = van_ban.strip()
    if len(van_ban) <= kich_thuoc:
        return [van_ban] if van_ban else []
    ket_qua, bat_dau = [], 0
    while bat_dau < len(van_ban):
        ket_qua.append(van_ban[bat_dau : bat_dau + kich_thuoc])
        if bat_dau + kich_thuoc >= len(van_ban):
            break
        bat_dau += kich_thuoc - chong_lan
    return ket_qua


def _cau_dau(van_ban: str | None) -> str:
    if not van_ban:
        return ""
    return _DAU_CAU.split(van_ban.strip(), maxsplit=1)[0]


def chia_theo_tieu_de(markdown: str) -> list[str]:
    """Tách Markdown theo tiêu đề (`#`), mỗi phần rồi cắt tiếp theo `KICH_THUOC_DOAN`."""
    phan, hien_tai = [], []
    for dong in markdown.splitlines():
        if dong.lstrip().startswith("#") and hien_tai:
            phan.append("\n".join(hien_tai))
            hien_tai = []
        hien_tai.append(dong)
    if hien_tai:
        phan.append("\n".join(hien_tai))
    return [d for p in phan for d in chia_doan(p)]


async def _doan_san_pham(db: AsyncSession) -> list[Doan]:
    sp_ds = (
        await db.execute(
            select(SanPham, DanhMuc.ten)
            .join(DanhMuc, DanhMuc.id == SanPham.danh_muc_id)
            .where(SanPham.deleted_at.is_(None), SanPham.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh)
            .order_by(SanPham.id)
        )
    ).all()
    hoat_chat: dict[int, list[str]] = {}
    for sp_id, ten, ham_luong in (
        await db.execute(
            select(ThanhPhan.san_pham_id, HoatChat.ten, ThanhPhan.ham_luong)
            .join(HoatChat, HoatChat.id == ThanhPhan.hoat_chat_id)
            .order_by(ThanhPhan.san_pham_id, HoatChat.ten)
        )
    ).all():
        hoat_chat.setdefault(sp_id, []).append(f"{ten} {ham_luong}".strip() if ham_luong else ten)
    # Bản đã duyệt mới nhất của từng sản phẩm
    moi_nhat = (
        select(ThongTinChuyenMon.san_pham_id, func.max(ThongTinChuyenMon.phien_ban).label("pb"))
        .where(ThongTinChuyenMon.trang_thai == TrangThaiNoiDung.da_duyet)
        .group_by(ThongTinChuyenMon.san_pham_id)
        .subquery()
    )
    cm = {
        t.san_pham_id: t
        for t in (
            await db.execute(
                select(ThongTinChuyenMon).join(
                    moi_nhat,
                    (moi_nhat.c.san_pham_id == ThongTinChuyenMon.san_pham_id)
                    & (moi_nhat.c.pb == ThongTinChuyenMon.phien_ban),
                )
            )
        ).scalars()
    }
    ket_qua: list[Doan] = []
    for sp, ten_dm in sp_ds:
        loai = _gt(sp.loai_san_pham)
        meta = {
            "san_pham_id": sp.id,
            "loai_san_pham": loai,
            "can_ke_don": loai == "thuoc_ke_don",
            "danh_muc_id": sp.danh_muc_id,
        }
        hc = hoat_chat.get(sp.id, [])
        hc_ten = ", ".join(hc)
        t = cm.get(sp.id)
        tong_quan = f"{sp.ten}. Loại: {loai}. Danh mục: {ten_dm}."
        if hc_ten:
            tong_quan += f" Hoạt chất: {hc_ten}."
        if t is not None and _cau_dau(t.chi_dinh):
            tong_quan += f" Chỉ định: {_cau_dau(t.chi_dinh)}"
        ket_qua.append(
            Doan(
                NguonTriThuc.san_pham,
                sp.id,
                "tong_quan",
                0,
                tong_quan,
                sp.id,
                {**meta, "loai_nguon": "tong_quan", "doan": 0},
            )
        )
        if t is None:
            continue
        tien_to = f"Sản phẩm: {sp.ten} ({hc_ten}). " if hc_ten else f"Sản phẩm: {sp.ten}. "
        for truong in TRUONG_CHUYEN_MON:
            gia_tri = getattr(t, truong)
            for i, d in enumerate(chia_doan(gia_tri or "")):
                ket_qua.append(
                    Doan(
                        NguonTriThuc.san_pham, t.id, truong, i, f"{tien_to}Mục: {NHAN_TRUONG[truong]}. {d}", sp.id,
                        {**meta, "loai_nguon": "chuyen_mon", "doan": i},
                    )
                )  # fmt: skip
    return ket_qua


async def _doan_bai_viet(db: AsyncSession) -> list[Doan]:
    cau = select(BaiViet).where(
        BaiViet.trang_thai == TrangThaiNoiDung.da_duyet,
        (BaiViet.loai != LoaiBaiViet.bai_viet) | (BaiViet.dua_vao_ai.is_(True)),
    )
    nguon = {
        LoaiBaiViet.bai_viet: NguonTriThuc.bai_viet,
        LoaiBaiViet.chinh_sach: NguonTriThuc.chinh_sach,
        LoaiBaiViet.faq: NguonTriThuc.faq,
    }
    ket_qua = []
    for b in (await db.execute(cau.order_by(BaiViet.id))).scalars():
        for i, d in enumerate(chia_theo_tieu_de(f"# {b.tieu_de}\n{b.noi_dung}")):
            meta = {
                "san_pham_id": None,
                "loai_san_pham": None,
                "can_ke_don": False,
                "danh_muc_id": None,
                "loai_nguon": _gt(b.loai),
                "doan": i,
            }
            ket_qua.append(Doan(nguon[LoaiBaiViet(_gt(b.loai))], b.id, "noi_dung", i, d, None, meta))
    return ket_qua


async def doan_mong_muon(db: AsyncSession) -> list[Doan]:
    return [*await _doan_san_pham(db), *await _doan_bai_viet(db)]


async def dong_bo(db: AsyncSession) -> KetQuaDongBo:
    """Đồng bộ toàn bộ kho tri thức trong transaction của người gọi; đang có lần đồng bộ khác chạy thì `409`."""
    if not await db.scalar(text("SELECT pg_try_advisory_xact_lock(hashtext(:k))"), {"k": KHOA_TU_VAN}):
        raise LoiNghiepVu("TRUNG_DU_LIEU", "Đang có một lần đồng bộ kho tri thức khác chạy")
    mo_hinh = embedding.ten_mo_hinh()
    mong_muon = {d.khoa: d for d in await doan_mong_muon(db)}
    hien_co = {
        (_gt(r.nguon_loai), r.nguon_id, r.truong or "", int((r.metadata_ or {}).get("doan", 0))): r
        for r in (await db.execute(select(TaiLieuTriThuc))).scalars()
    }
    kq = KetQuaDongBo(mo_hinh=mo_hinh)
    can_embed: list[tuple[Doan, TaiLieuTriThuc | None]] = []
    for khoa, d in mong_muon.items():
        r = hien_co.get(khoa)
        if r is None:
            can_embed.append((d, None))
        elif r.hash_noi_dung == d.hash and r.mo_hinh_embedding == mo_hinh and r.embedding is not None:
            if (
                r.metadata_ != d.metadata or r.san_pham_id != d.san_pham_id
            ):  # chỉ siêu dữ liệu đổi: không cần vector mới
                r.metadata_, r.san_pham_id, r.updated_at = d.metadata, d.san_pham_id, bay_gio_utc()
                kq.sua += 1
            else:
                kq.bo_qua += 1
        else:
            can_embed.append((d, r))
    for i in range(0, len(can_embed), LO_EMBED):
        lo = can_embed[i : i + LO_EMBED]
        vectors = await embedding.embed([d.noi_dung for d, _ in lo])
        for (d, r), v in zip(lo, vectors, strict=True):
            if r is None:
                db.add(
                    TaiLieuTriThuc(
                        nguon_loai=d.nguon_loai, nguon_id=d.nguon_id, san_pham_id=d.san_pham_id, truong=d.truong,
                        noi_dung=d.noi_dung, metadata_=d.metadata, embedding=v, mo_hinh_embedding=mo_hinh,
                        hash_noi_dung=d.hash,
                    )
                )  # fmt: skip
                kq.them += 1
            else:
                r.noi_dung, r.metadata_, r.san_pham_id, r.embedding = d.noi_dung, d.metadata, d.san_pham_id, v
                r.mo_hinh_embedding, r.hash_noi_dung, r.updated_at = mo_hinh, d.hash, bay_gio_utc()
                kq.sua += 1
    thua = [r.id for khoa, r in hien_co.items() if khoa not in mong_muon]
    if thua:
        await db.execute(delete(TaiLieuTriThuc).where(TaiLieuTriThuc.id.in_(thua)))
    kq.xoa = len(thua)
    await db.flush()
    kq.tong_doan = await db.scalar(select(func.count()).select_from(TaiLieuTriThuc)) or 0
    return kq


class ThongKeTriThuc(BaseModel):
    tong_doan: int
    theo_nguon: dict[str, int]
    mo_hinh_hien_tai: str
    mo_hinh_trong_kho: list[str]
    cap_nhat_gan_nhat: Any = None
    can_dong_bo_lai_vector: bool
    """Có đoạn dùng mô hình embedding khác mô hình đang cấu hình: đồng bộ sẽ tạo lại vector."""


async def thong_ke(db: AsyncSession) -> ThongKeTriThuc:
    theo_nguon = dict(
        (await db.execute(select(TaiLieuTriThuc.nguon_loai, func.count()).group_by(TaiLieuTriThuc.nguon_loai))).all()
    )
    mo_hinh_kho = sorted(
        m for m in (await db.execute(select(TaiLieuTriThuc.mo_hinh_embedding).distinct())).scalars() if m is not None
    )
    hien_tai = embedding.ten_mo_hinh()
    return ThongKeTriThuc(
        tong_doan=sum(theo_nguon.values()),
        theo_nguon={_gt(k): v for k, v in theo_nguon.items()},
        mo_hinh_hien_tai=hien_tai,
        mo_hinh_trong_kho=mo_hinh_kho,
        cap_nhat_gan_nhat=await db.scalar(select(func.max(TaiLieuTriThuc.updated_at))),
        can_dong_bo_lai_vector=any(m != hien_tai for m in mo_hinh_kho),
    )
