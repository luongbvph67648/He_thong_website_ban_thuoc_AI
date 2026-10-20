"""Chatbot tư vấn (KVL05: AI02 + AI03), spec 07 mục 4. Chỉ đọc, mọi bộ lọc an toàn nằm ở SQL.

Luồng một lượt (`chay_luot`): luật dấu hiệu nguy hiểm -> AI02 phân loại -> AI03 trả lời có tool chỉ đọc -> thẻ sản phẩm.
Mọi lỗi AI (tắt, hết ngân sách, từ chối, lỗi mạng) đều quay về đề nghị gặp dược sĩ, không bao giờ trả lỗi thô cho khách.
"""

import json
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import claude, embedding
from app.ai.dau_hieu import MAU_NGUY_HIEM, tim_dau_hieu
from app.core.phan_trang import ThamSoPhanTrang
from app.core.thoi_gian import hom_nay_vn
from app.models.ai import TaiLieuTriThuc
from app.models.ban_hang import DonHang, LichSuTrangThai
from app.models.enums import LoaiSanPham, NguonTriThuc
from app.models.khach_hang import DiUng, HoSoSucKhoe, KhachHang
from app.models.san_pham import HoatChat, SanPham
from app.modules.chuyen_mon.noi_dung import noi_dung_da_duyet
from app.modules.cua_hang import tim_kiem, tim_kiem_lai
from app.modules.cua_hang.loc_an_toan import di_ung_cua_khach, loc_tri_thuc_san_pham, the_hop_le
from app.modules.cua_hang.schemas import SanPhamThe

logger = logging.getLogger(__name__)

THU_MUC_PROMPT = Path(__file__).parent / "prompts"
LUU_Y_THAM_KHAO = "Thông tin chỉ mang tính tham khảo, không thay thế tư vấn của dược sĩ/bác sĩ."
MAU_CHUYEN_DUOC_SI = (
    'Câu hỏi này nên có dược sĩ hỗ trợ trực tiếp để bạn được tư vấn chính xác. Bạn bấm nút "Gặp dược sĩ" bên dưới nhé.'
)
MAU_AI_KHONG_KHA_DUNG = (
    'Trợ lý AI tạm thời không trả lời được lúc này. Bạn bấm "Gặp dược sĩ" để được hỗ trợ trực tiếp nhé.'
)
MAU_Y_DINH = (
    "hoi_san_pham", "cach_dung", "trieu_chung", "chinh_sach", "don_hang", "can_duoc_si", "ngoai_pham_vi", "khac",
)  # fmt: skip
SO_TIN_LICH_SU = 20
TOI_DA_THE_SAN_PHAM = 5
TOP_DOAN = 5

_cache_prompt: dict[str, str] = {}


def doc_prompt(ten: str) -> str:
    if ten not in _cache_prompt:
        _cache_prompt[ten] = (THU_MUC_PROMPT / ten).read_text(encoding="utf-8")
    return _cache_prompt[ten]


def system_chat(loi_nhac_bo_sung: str) -> str:
    """System prompt cố định; chỉ nối `ai_loi_nhac_bo_sung` (đổi hiếm) nên prompt caching vẫn hiệu lực."""
    goc = doc_prompt("chat_he_thong.md")
    return f"{goc}\n\n## Lời nhắc bổ sung của nhà thuốc\n{loi_nhac_bo_sung}" if loi_nhac_bo_sung.strip() else goc


# --- AI02 ---

PHAN_LOAI_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "y_dinh": {"type": "string", "enum": list(MAU_Y_DINH)},
        "nguy_hiem": {"type": "boolean"},
        "can_chuyen_duoc_si": {"type": "boolean"},
        "do_tu_tin": {"type": "number"},
    },
    "required": ["y_dinh", "nguy_hiem", "can_chuyen_duoc_si", "do_tu_tin"],
    "additionalProperties": False,
}


class PhanLoai(BaseModel):
    y_dinh: Literal[
        "hoi_san_pham", "cach_dung", "trieu_chung", "chinh_sach", "don_hang", "can_duoc_si", "ngoai_pham_vi", "khac"
    ]
    nguy_hiem: bool
    can_chuyen_duoc_si: bool
    do_tu_tin: float = Field(ge=0, le=1)


async def phan_loai(noi_dung: str, su_dung: claude.SuDung) -> PhanLoai:
    """AI02; kiểm lại kết quả bằng Pydantic. Sai định dạng thì `AiLoi`."""
    kq = await claude.goi_json(
        system=doc_prompt("chat_phan_loai.md"),
        noi_dung=[{"type": "text", "text": noi_dung}],
        schema=PHAN_LOAI_SCHEMA,
        effort="low",
        max_tokens=1000,
        su_dung=su_dung,
    )
    try:
        return PhanLoai.model_validate(kq)
    except ValidationError as e:
        raise claude.AiLoi("Kết quả phân loại sai định dạng") from e


# --- Tool chỉ đọc ---


def _tool(ten: str, mo_ta: str, thuoc_tinh: dict[str, Any], bat_buoc: list[str]) -> dict[str, Any]:
    return {
        "name": ten,
        "description": mo_ta,
        "strict": True,
        "eager_input_streaming": True,
        "input_schema": {
            "type": "object",
            "properties": thuoc_tinh,
            "required": bat_buoc,
            "additionalProperties": False,
        },
    }


_CHUOI = {"type": "string"}
TOOLS: list[dict[str, Any]] = [  # thứ tự cố định để prompt caching hiệu lực
    _tool(
        "tim_san_pham",
        "Tìm sản phẩm không kê đơn đang bán theo tên, hoạt chất, triệu chứng hoặc công dụng.",
        {
            "tu_khoa": {**_CHUOI, "description": "Từ khóa hoặc mô tả nhu cầu"},
            "so_luong": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        },
        ["tu_khoa", "so_luong"],
    ),
    _tool(
        "xem_san_pham",
        "Xem thông tin chuyên môn đã duyệt, giá và tình trạng còn hàng của một sản phẩm.",
        {"san_pham_id": {"type": "integer"}},
        ["san_pham_id"],
    ),
    _tool(
        "tra_cuu_kien_thuc",
        "Tra cứu kiến thức chung về sức khỏe và cách dùng thuốc không kê đơn từ kho tri thức đã duyệt.",
        {"cau_hoi": _CHUOI},
        ["cau_hoi"],
    ),
    _tool(
        "tra_cuu_chinh_sach",
        "Tra cứu chính sách và câu hỏi thường gặp của nhà thuốc (giao hàng, đổi trả, thanh toán).",
        {"cau_hoi": _CHUOI},
        ["cau_hoi"],
    ),
    _tool(
        "xem_don_hang",
        "Xem trạng thái và dòng thời gian của đơn hàng thuộc về chính khách đang đăng nhập.",
        {"ma_don": _CHUOI},
        ["ma_don"],
    ),
    _tool(
        "de_nghi_gap_duoc_si",
        "Đề nghị khách gặp dược sĩ khi câu hỏi cần chuyên môn trực tiếp hoặc ngoài khả năng của trợ lý.",
        {"ly_do": _CHUOI},
        ["ly_do"],
    ),
]


class TimSanPhamIn(BaseModel):
    tu_khoa: str = Field(min_length=1, max_length=100)
    so_luong: int = Field(ge=1, le=5)


class XemSanPhamIn(BaseModel):
    san_pham_id: int = Field(ge=1, le=2_147_483_647)


class CauHoiIn(BaseModel):
    cau_hoi: str = Field(min_length=1, max_length=300)


class XemDonIn(BaseModel):
    ma_don: str = Field(min_length=1, max_length=20)


class GapDuocSiIn(BaseModel):
    ly_do: str = Field(min_length=1, max_length=300)


TRUONG_CHUYEN_MON = (
    "chi_dinh", "chong_chi_dinh", "lieu_dung_tham_khao", "tac_dung_phu", "than_trong", "tuong_tac_thuoc",
    "phu_nu_co_thai_cho_con_bu", "tre_em", "qua_lieu_xu_tri", "bao_quan",
)  # fmt: skip


@dataclass
class NguCanh:
    """Trạng thái một lượt: ai hỏi, hoạt chất dị ứng, id sản phẩm tool đã trả, cờ đề nghị gặp dược sĩ."""

    db: AsyncSession
    khach: KhachHang | None
    ids_di_ung: list[int] = field(default_factory=list)
    san_pham_xuat_hien: list[int] = field(default_factory=list)
    de_nghi_duoc_si: bool = False
    ly_do_duoc_si: str | None = None


async def tim_doan(db: AsyncSession, cau_hoi: str, nguon: list[NguonTriThuc], so_doan: int) -> list[dict[str, Any]]:
    """Đoạn tri thức gần câu hỏi nhất; luôn lọc `can_ke_don = false` trong SQL."""
    (vec,) = await embedding.embed([cau_hoi])
    kc = TaiLieuTriThuc.embedding.cosine_distance(vec)
    cau = (
        select(TaiLieuTriThuc.noi_dung, TaiLieuTriThuc.nguon_loai, kc.label("kc"))
        .where(
            TaiLieuTriThuc.embedding.is_not(None),
            TaiLieuTriThuc.mo_hinh_embedding == embedding.ten_mo_hinh(),
            TaiLieuTriThuc.nguon_loai.in_(nguon),
            TaiLieuTriThuc.metadata_["can_ke_don"].astext == "false",
            await loc_tri_thuc_san_pham(db),
        )
        .order_by(kc)
        .limit(so_doan)
    )
    return [
        {"noi_dung": nd, "nguon": getattr(loai, "value", loai)}
        for nd, loai, khoang_cach in (await db.execute(cau)).all()
        if khoang_cach <= tim_kiem_lai.NGUONG_KHOANG_CACH
    ]


def _the_ra(the: list[SanPhamThe]) -> list[dict[str, Any]]:
    return [
        {
            "san_pham_id": t.id,
            "ten": t.ten,
            "gia_tu": str(t.gia) if t.gia is not None else None,
            "don_vi": t.ten_don_vi_gia,
            "con_hang": t.con_hang,
        }
        for t in the
    ]


async def _chay_tool(ten: str, thamso: dict[str, Any], ctx: NguCanh) -> Any:
    db = ctx.db
    if ten == "tim_san_pham":
        vao = TimSanPhamIn.model_validate(thamso)
        q = tim_kiem.chuan_hoa_tu_khoa(vao.tu_khoa)
        if len(q) < tim_kiem.TOI_THIEU_KY_TU:
            return []
        lai = await tim_kiem_lai.tim_lai(db, q, ThamSoPhanTrang(1, vao.so_luong), chi_khong_ke_don=True)
        the = await the_hop_le(db, [t.id for t in lai.trang.du_lieu], ctx.ids_di_ung)
        ctx.san_pham_xuat_hien += [t.id for t in the]
        return _the_ra(the)
    if ten == "xem_san_pham":
        vao = XemSanPhamIn.model_validate(thamso)
        loai = await db.scalar(
            select(SanPham.loai_san_pham).where(SanPham.id == vao.san_pham_id, SanPham.deleted_at.is_(None))
        )
        if loai is None:
            return {"khong_tim_thay": True}
        if getattr(loai, "value", loai) == LoaiSanPham.thuoc_ke_don.value:
            return {"can_tu_van_duoc_si": True}  # thuốc kê đơn: không trả bất cứ thông tin nào khác
        the = await the_hop_le(db, [vao.san_pham_id], ctx.ids_di_ung)
        if not the:
            return {"khong_tim_thay": True}
        ctx.san_pham_xuat_hien.append(vao.san_pham_id)
        nd = await noi_dung_da_duyet(db, vao.san_pham_id)
        return {
            **_the_ra(the)[0],
            "thong_tin_chuyen_mon": {k: getattr(nd, k) for k in TRUONG_CHUYEN_MON if nd and getattr(nd, k)}
            if nd
            else {},
        }
    if ten == "tra_cuu_kien_thuc":
        vao = CauHoiIn.model_validate(thamso)
        return await tim_doan(db, vao.cau_hoi, [NguonTriThuc.san_pham, NguonTriThuc.bai_viet], TOP_DOAN)
    if ten == "tra_cuu_chinh_sach":
        vao = CauHoiIn.model_validate(thamso)
        return await tim_doan(db, vao.cau_hoi, [NguonTriThuc.chinh_sach, NguonTriThuc.faq], 3)
    if ten == "xem_don_hang":
        vao = XemDonIn.model_validate(thamso)
        if ctx.khach is None:
            return {"can_dang_nhap": True}
        don = (
            await db.execute(
                select(DonHang).where(
                    DonHang.ma_don == vao.ma_don.strip().upper(), DonHang.khach_hang_id == ctx.khach.id
                )
            )
        ).scalar_one_or_none()
        if don is None:
            return {"khong_tim_thay": True}  # đơn của người khác cũng chỉ là "không thấy"
        moc = (
            await db.execute(
                select(LichSuTrangThai.den_trang_thai, LichSuTrangThai.created_at)
                .where(LichSuTrangThai.don_hang_id == don.id)
                .order_by(LichSuTrangThai.created_at, LichSuTrangThai.id)
            )
        ).all()
        gt = lambda x: getattr(x, "value", x)  # noqa: E731
        return {
            "ma_don": don.ma_don,
            "trang_thai": gt(don.trang_thai),
            "thanh_toan": gt(don.trang_thai_tt),
            "tong_tien": str(don.tong_tien),
            "dong_thoi_gian": [{"trang_thai": gt(t), "luc": luc.isoformat()} for t, luc in moc],
        }
    if ten == "de_nghi_gap_duoc_si":
        vao = GapDuocSiIn.model_validate(thamso)
        ctx.de_nghi_duoc_si, ctx.ly_do_duoc_si = True, vao.ly_do[:100]
        return {"ok": True}
    raise ValueError("Tool không tồn tại")


def tao_thuc_thi_tool(ctx: NguCanh) -> Callable[[Any], Any]:
    async def thuc_thi(block: Any) -> dict[str, Any]:
        """Eager input streaming: API không kiểm input nên PHẢI validate (Pydantic) trước khi chạy tool."""
        try:
            kq = await _chay_tool(block.name, block.input if isinstance(block.input, dict) else {}, ctx)
        except (ValidationError, ValueError):
            return {"type": "tool_result", "tool_use_id": block.id, "content": "Tham số không hợp lệ", "is_error": True}
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(kq, ensure_ascii=False, default=str),
        }

    return thuc_thi


# --- Một lượt chat ---


@dataclass
class KetQuaLuot:
    """Kết quả để lưu `tin_nhan` sau lượt."""

    noi_dung: str = ""
    y_dinh: str | None = None
    san_pham_goi_y: list[int] = field(default_factory=list)
    nguy_hiem: bool = False
    chuyen_duoc_si: bool = False
    ly_do_chuyen: str | None = None
    su_dung: claude.SuDung = field(default_factory=claude.SuDung)


def chuoi_lich_su(
    tin_truoc: list[tuple[str, str]], cau_hoi: str, ngu_canh_suc_khoe: str | None
) -> list[dict[str, Any]]:
    """Lịch sử gửi Claude: CHỈ phần text các lượt trước (khách/ai), xen kẽ vai trò, kết thúc bằng câu hỏi mới."""
    ds: list[dict[str, Any]] = []
    for vai_tro, nd in tin_truoc[-SO_TIN_LICH_SU:]:
        vt = "user" if vai_tro == "khach" else "assistant"
        if ds and ds[-1]["role"] == vt:
            ds[-1]["content"] += "\n" + nd
        else:
            ds.append({"role": vt, "content": nd})
    while ds and ds[0]["role"] != "user":
        ds.pop(0)
    if ds and ds[-1]["role"] == "user":  # hai lượt khách liên tiếp (lượt trước chưa có trả lời): gộp
        ds[-1]["content"] += "\n" + cau_hoi
    else:
        ds.append({"role": "user", "content": cau_hoi})
    if ngu_canh_suc_khoe:
        ds[-1]["content"] += f"\n\n[Ngữ cảnh khách đã đồng ý chia sẻ: {ngu_canh_suc_khoe}]"
    return ds


async def ngu_canh_suc_khoe(db: AsyncSession, khach: KhachHang | None) -> str | None:
    """Chỉ phần cần thiết (hoạt chất dị ứng, mang thai/cho con bú, nhóm tuổi), khi khách đã đồng ý. Không gửi tên, SĐT,
    bệnh nền hay ghi chú."""
    if khach is None:
        return None
    ho_so = await db.scalar(select(HoSoSucKhoe).where(HoSoSucKhoe.khach_hang_id == khach.id))
    if ho_so is None or not ho_so.dong_y_su_dung:
        return None
    phan = []
    if ho_so.dang_mang_thai:
        phan.append("đang mang thai")
    if ho_so.dang_cho_con_bu:
        phan.append("đang cho con bú")
    if ho_so.nam_sinh:
        tuoi = hom_nay_vn().year - ho_so.nam_sinh
        phan.append("trẻ em" if tuoi < 12 else "người cao tuổi" if tuoi >= 65 else "người lớn")
    ten_di_ung = list(
        (
            await db.execute(
                select(HoatChat.ten)
                .join(DiUng, DiUng.hoat_chat_id == HoatChat.id)
                .where(DiUng.khach_hang_id == khach.id)
                .order_by(HoatChat.ten)
            )
        ).scalars()
    )
    if ten_di_ung:
        phan.append("dị ứng hoạt chất: " + ", ".join(ten_di_ung))
    return "; ".join(phan) or None


async def chay_luot(
    *,
    db: AsyncSession,
    khach: KhachHang | None,
    cau_hoi: str,
    tin_truoc: list[tuple[str, str]],
    ds_dau_hieu: list[str],
    nguong_chuyen: float,
    loi_nhac: str,
    chat_bat: bool,
    het_ngan_sach: bool,
) -> AsyncIterator[dict[str, Any]]:
    """Sinh các sự kiện `{loai, ...}` của SSE; sự kiện cuối `ket_thuc` mang kết quả (`ket_qua`) để nơi gọi lưu DB."""
    kq = KetQuaLuot()

    def chuyen(thong_diep: str, ly_do: str):
        kq.chuyen_duoc_si, kq.ly_do_chuyen = True, ly_do
        if not kq.noi_dung:
            kq.noi_dung = thong_diep
        return {"loai": "chuyen_duoc_si", "ly_do": ly_do, "thong_diep": thong_diep}

    # 1. Luật dấu hiệu nguy hiểm: trước mọi lời gọi Claude
    cum = tim_dau_hieu(cau_hoi, ds_dau_hieu)
    if cum is not None:
        kq.nguy_hiem, kq.noi_dung, kq.y_dinh = True, MAU_NGUY_HIEM, "nguy_hiem"
        yield {"loai": "nguy_hiem", "noi_dung": MAU_NGUY_HIEM}
        yield {"loai": "ket_thuc", "ket_qua": kq}
        return
    if not chat_bat or het_ngan_sach:
        yield chuyen(MAU_AI_KHONG_KHA_DUNG, "ai_khong_kha_dung")
        yield {"loai": "ket_thuc", "ket_qua": kq}
        return
    try:
        # 2. AI02
        pl = await phan_loai(cau_hoi, kq.su_dung)
        kq.y_dinh = pl.y_dinh
        if pl.nguy_hiem:
            kq.nguy_hiem, kq.noi_dung = True, MAU_NGUY_HIEM
            yield {"loai": "nguy_hiem", "noi_dung": MAU_NGUY_HIEM}
            yield {"loai": "ket_thuc", "ket_qua": kq}
            return
        if pl.can_chuyen_duoc_si or pl.y_dinh in ("can_duoc_si", "ngoai_pham_vi"):
            yield chuyen(MAU_CHUYEN_DUOC_SI, "can_duoc_si")
            yield {"loai": "ket_thuc", "ket_qua": kq}
            return
        # 3. AI03
        ctx = NguCanh(db=db, khach=khach, ids_di_ung=await di_ung_cua_khach(db, khach))
        lich_su = chuoi_lich_su(tin_truoc, cau_hoi, await ngu_canh_suc_khoe(db, khach))
        doan_chu: list[str] = []
        async for doan in claude.stream_chat(
            system=system_chat(loi_nhac),
            lich_su=lich_su,
            tools=TOOLS,
            thuc_thi_tool=tao_thuc_thi_tool(ctx),
            effort="medium",
            su_dung=kq.su_dung,
        ):
            doan_chu.append(doan)
            yield {"loai": "van_ban", "noi_dung": doan}
        kq.noi_dung = "".join(doan_chu).strip()
        if not kq.noi_dung:
            raise claude.AiLoi("Trả lời rỗng")
        yield {"loai": "van_ban", "noi_dung": f"\n\n{LUU_Y_THAM_KHAO}"}
        kq.noi_dung += f"\n\n{LUU_Y_THAM_KHAO}"
        the = await the_hop_le(db, list(dict.fromkeys(ctx.san_pham_xuat_hien)), ctx.ids_di_ung)
        the = the[:TOI_DA_THE_SAN_PHAM]
        if the:
            kq.san_pham_goi_y = [t.id for t in the]
            yield {"loai": "the_san_pham", "san_pham": [t.model_dump(mode="json") for t in the]}
        if ctx.de_nghi_duoc_si or pl.do_tu_tin < nguong_chuyen:
            yield chuyen(MAU_CHUYEN_DUOC_SI, ctx.ly_do_duoc_si or "do_tu_tin_thap")
    except claude.AiTuChoi:
        yield chuyen(MAU_CHUYEN_DUOC_SI, "ai_tu_choi")
    except claude.AiLoi:
        logger.warning("Chatbot lỗi AI, chuyển dược sĩ")
        yield chuyen(MAU_AI_KHONG_KHA_DUNG, "ai_loi")
    yield {"loai": "ket_thuc", "ket_qua": kq}
