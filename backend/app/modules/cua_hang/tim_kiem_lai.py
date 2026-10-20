"""Tìm kiếm lai AI01 (T7.2, spec 07 mục 5): từ khóa (trigram, T2.5) + ngữ nghĩa (vector) ghép bằng RRF.

Tìm được theo triệu chứng/công dụng ("đau đầu") nhờ các đoạn tri thức. AI tắt hoặc lỗi (embedding, vector, CSDL chưa có
đoạn) thì quay về chỉ từ khóa và `che_do = tu_khoa`. Giá và tồn kho không nằm trong vector: thẻ luôn dựng từ CSDL.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import embedding
from app.core.phan_trang import ThamSoPhanTrang, Trang, tao_trang
from app.models.ai import TaiLieuTriThuc
from app.models.san_pham import SanPham
from app.modules.ai_quan_tri.cau_hinh_ai import module_bat
from app.modules.cua_hang import tim_kiem
from app.modules.cua_hang.danh_sach import chon_the, dung_the
from app.modules.cua_hang.hien_thi import CayHienThi, la_hien_thi, nap_cay_hien_thi
from app.modules.cua_hang.loc_an_toan import loc_tri_thuc_san_pham
from app.modules.cua_hang.schemas import SanPhamThe

logger = logging.getLogger(__name__)

K_RRF = 60
SO_TU_KHOA = 50
SO_DOAN_NGU_NGHIA = 100
TOI_DA_KET_QUA = 150
NGUONG_KHOANG_CACH = 0.55
"""Khoảng cách cosine tối đa của đoạn để coi là liên quan (đoạn xa hơn là nhiễu)."""
THUONG_CON_HANG = 0.002
"""Điểm cộng nhỏ cho sản phẩm còn hàng, chỉ phá hòa giữa các sản phẩm gần điểm nhau."""


@dataclass
class KetQuaTimLai:
    trang: Trang[SanPhamThe]
    che_do: str  # "hybrid" | "tu_khoa"


async def id_ngu_nghia(db: AsyncSession, q: str, *, chi_khong_ke_don: bool = False) -> list[int]:
    """Id sản phẩm xếp theo đoạn tri thức gần câu hỏi nhất (cosine), mỗi sản phẩm một lần, tối đa 100 đoạn gần nhất."""
    (vec,) = await embedding.embed([q])
    kc = TaiLieuTriThuc.embedding.cosine_distance(vec)
    cau = (
        select(TaiLieuTriThuc.san_pham_id, kc.label("kc"))
        .where(
            TaiLieuTriThuc.san_pham_id.is_not(None),
            TaiLieuTriThuc.embedding.is_not(None),
            TaiLieuTriThuc.mo_hinh_embedding == embedding.ten_mo_hinh(),
        )
        .order_by(kc)
        .limit(SO_DOAN_NGU_NGHIA)
    )
    if chi_khong_ke_don:  # ngữ cảnh chatbot: lọc ngay trong SQL (spec 07 mục 1.2)
        cau = cau.where(TaiLieuTriThuc.metadata_["can_ke_don"].astext == "false", await loc_tri_thuc_san_pham(db))
    tot_nhat: dict[int, float] = {}
    for sp_id, khoang_cach in (await db.execute(cau)).all():
        if khoang_cach <= NGUONG_KHOANG_CACH:
            tot_nhat.setdefault(sp_id, khoang_cach)  # kết quả đã sắp theo khoảng cách nên lần đầu là tốt nhất
    return list(tot_nhat)


def ghep_rrf(*danh_sach: list[int]) -> dict[int, float]:
    """Reciprocal Rank Fusion: điểm = tổng 1/(60 + hạng) qua các danh sách (hạng bắt đầu từ 1)."""
    diem: dict[int, float] = {}
    for ds in danh_sach:
        for hang, sp_id in enumerate(ds, start=1):
            diem[sp_id] = diem.get(sp_id, 0.0) + 1.0 / (K_RRF + hang)
    return diem


async def tim_lai(
    db: AsyncSession, q: str, tp: ThamSoPhanTrang, cay: CayHienThi | None = None, *, chi_khong_ke_don: bool = False
) -> KetQuaTimLai:
    """Kết quả cho từ khóa đã chuẩn hóa. Không bao giờ ném lỗi do AI: quay về từ khóa."""
    cay = cay or await nap_cay_hien_thi(db)
    if len(q) < tim_kiem.TOI_THIEU_KY_TU:
        return KetQuaTimLai(tao_trang([], 0, tp), "tu_khoa")

    async def chi_tu_khoa() -> KetQuaTimLai:
        return KetQuaTimLai(await tim_kiem.tim_san_pham(db, q, tp, cay), "tu_khoa")

    if not await module_bat(db, "tim_kiem"):
        return await chi_tu_khoa()
    try:
        async with db.begin_nested():  # savepoint: lỗi vector không làm hỏng transaction của request
            ngu_nghia = await id_ngu_nghia(db, q, chi_khong_ke_don=chi_khong_ke_don)
    except Exception:  # noqa: BLE001  mọi lỗi AI/vector đều quay về từ khóa
        logger.warning("Tìm kiếm ngữ nghĩa lỗi, quay về từ khóa", exc_info=True)
        return await chi_tu_khoa()
    if not ngu_nghia:
        return await chi_tu_khoa()
    the_tu_khoa = (await tim_kiem.tim_san_pham(db, q, ThamSoPhanTrang(1, SO_TU_KHOA), cay, dem_tong=False)).du_lieu
    if chi_khong_ke_don:
        the_tu_khoa = [t for t in the_tu_khoa if t.loai_san_pham != "thuoc_ke_don"]
    diem = ghep_rrf([t.id for t in the_tu_khoa], ngu_nghia)
    the_theo_id = {t.id: t for t in the_tu_khoa}
    thieu = [i for i in diem if i not in the_theo_id]
    if thieu:
        dieu_kien = [la_hien_thi(cay.ids), SanPham.id.in_(thieu)]
        if chi_khong_ke_don:
            dieu_kien.append(SanPham.loai_san_pham != "thuoc_ke_don")
        dong = (await db.execute(chon_the().where(*dieu_kien))).all()
        the_theo_id.update({t.id: t for t in await dung_the(db, dong)})
    ton = {i: t.con_hang for i, t in the_theo_id.items()}
    xep = sorted(
        (i for i in diem if i in the_theo_id),  # sản phẩm không còn hiển thị bị loại ở đây
        key=lambda i: (-(diem[i] + (THUONG_CON_HANG if ton[i] else 0.0)), i),
    )[:TOI_DA_KET_QUA]
    trang = xep[tp.offset : tp.offset + tp.limit]
    return KetQuaTimLai(tao_trang([the_theo_id[i] for i in trang], len(xep), tp), "hybrid")
