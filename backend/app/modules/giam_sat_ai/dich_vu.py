"""DS12 (đánh giá câu trả lời AI) và AD11 (giám sát hội thoại AI). Mọi nội dung hội thoại ra khỏi module đều đã che
SĐT, email, tên (`core/an_danh`) và KHÔNG kèm id khách, mã phiên (bí mật truy cập chat) hay IP."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import ColumnElement, Select, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.an_danh import che_thong_tin
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_duoc_si
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import VN_TZ, hom_nay_vn
from app.models.ai import DanhGiaCauTraLoi, HoiThoai, LichSuTimKiem, TinNhan
from app.models.enums import LoaiHoiThoai, VaiTroTinNhan
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.modules.giam_sat_ai.schemas import (
    CauHoiPhoBien,
    DanhGiaDuocSiVao,
    DanhGiaTinNhanRa,
    HoiThoaiAnDanhChiTiet,
    HoiThoaiAnDanhTom,
    ThongKeAi,
    ThongKeDanhGia,
    TimKiemKhongKetQua,
    TinNhanAnDanh,
)

SO_NGAY_MAC_DINH = 30
SO_TU_KHOA_TOI_DA = 50
SO_CAU_HOI_PHO_BIEN = 10
DO_DAI_CAU_HOI_DAU = 120
TOI_THIEU_GHI_CHU_SAI = 3


def _khoang(tu_ngay: date | None, den_ngay: date | None) -> tuple[date, date, datetime, datetime]:
    """(từ, đến, mốc đầu, mốc cuối loại trừ) theo giờ VN; mặc định 30 ngày gần nhất, gồm cả hai đầu."""
    den = den_ngay or hom_nay_vn()
    tu = tu_ngay or den - timedelta(days=SO_NGAY_MAC_DINH - 1)
    if tu > den:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "tu_ngay", "loi": "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc"}],
        )
    dau = datetime(tu.year, tu.month, tu.day, tzinfo=VN_TZ)
    cuoi = datetime(den.year, den.month, den.day, tzinfo=VN_TZ) + timedelta(days=1)
    return tu, den, dau, cuoi


def _khach_bao_sai() -> ColumnElement[bool]:
    return exists().where(
        TinNhan.hoi_thoai_id == HoiThoai.id,
        DanhGiaCauTraLoi.tin_nhan_id == TinNhan.id,
        DanhGiaCauTraLoi.nguon == "khach",
        DanhGiaCauTraLoi.ket_qua == "khong_huu_ich",
    )


def la_bi_gan_co() -> ColumnElement[bool]:
    """Hội thoại bị hệ thống gắn cờ (dấu hiệu nguy hiểm) hoặc có tin AI bị khách báo "không hữu ích"."""
    return or_(HoiThoai.bi_gan_co.is_(True), _khach_bao_sai())


def _dem_tin(dieu_kien) -> ColumnElement[int]:
    return (
        select(func.count())
        .select_from(TinNhan)
        .where(TinNhan.hoi_thoai_id == HoiThoai.id, *dieu_kien)
        .correlate(HoiThoai)
        .scalar_subquery()
    )


def _dem_danh_gia(dieu_kien) -> ColumnElement[int]:
    return (
        select(func.count(func.distinct(DanhGiaCauTraLoi.tin_nhan_id)))
        .select_from(DanhGiaCauTraLoi)
        .join(TinNhan, TinNhan.id == DanhGiaCauTraLoi.tin_nhan_id)
        .where(TinNhan.hoi_thoai_id == HoiThoai.id, *dieu_kien)
        .correlate(HoiThoai)
        .scalar_subquery()
    )


def _cau_hoi_dau() -> ColumnElement[str | None]:
    return (
        select(TinNhan.noi_dung)
        .where(TinNhan.hoi_thoai_id == HoiThoai.id, TinNhan.vai_tro == VaiTroTinNhan.khach)
        .order_by(TinNhan.id)
        .limit(1)
        .correlate(HoiThoai)
        .scalar_subquery()
    )


def _chon_tom() -> Select:
    return select(
        HoiThoai,
        HoiThoai.khach_hang_id,
        _dem_tin([]).label("so_tin"),
        _dem_danh_gia([DanhGiaCauTraLoi.nguon == "khach", DanhGiaCauTraLoi.ket_qua == "khong_huu_ich"]).label(
            "bao_sai"
        ),
        _dem_danh_gia([DanhGiaCauTraLoi.nguon == "duoc_si"]).label("duoc_si_dg"),
        _cau_hoi_dau().label("cau_hoi_dau"),
    )


async def _ten_khach(db: AsyncSession, ids: set[int | None]) -> dict[int, str]:
    ids_that = [i for i in ids if i is not None]
    if not ids_that:
        return {}
    return dict((await db.execute(select(KhachHang.id, KhachHang.ho_ten).where(KhachHang.id.in_(ids_that)))).all())


async def _tom(db: AsyncSession, dong) -> list[HoiThoaiAnDanhTom]:
    ten = await _ten_khach(db, {d.khach_hang_id for d in dong})
    ra = []
    for d in dong:
        h: HoiThoai = d[0]
        cau = che_thong_tin(d.cau_hoi_dau, ten.get(d.khach_hang_id))
        ra.append(
            HoiThoaiAnDanhTom(
                id=h.id,
                created_at=h.created_at,
                loai=h.loai,
                trang_thai=h.trang_thai,
                bi_gan_co=h.bi_gan_co,
                ly_do_gan_co=h.ly_do_gan_co,
                so_tin_nhan=d.so_tin,
                so_khach_bao_sai=d.bao_sai,
                so_duoc_si_danh_gia=d.duoc_si_dg,
                cau_hoi_dau=cau if len(cau) <= DO_DAI_CAU_HOI_DAU else cau[: DO_DAI_CAU_HOI_DAU - 1] + "…",
                tong_token=h.tong_token,
                chi_phi=h.chi_phi,
            )
        )
    return ra


async def _chi_tiet(
    db: AsyncSession, hoi_thoai_id: int, nv: NhanVien | None, *, chi_gan_co: bool
) -> HoiThoaiAnDanhChiTiet:
    stmt = _chon_tom().where(HoiThoai.id == hoi_thoai_id)
    if chi_gan_co:
        stmt = stmt.where(la_bi_gan_co())
    dong = (await db.execute(stmt)).first()
    if dong is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy hội thoại")
    (tom,) = await _tom(db, [dong])
    ten = (await _ten_khach(db, {dong.khach_hang_id})).get(dong.khach_hang_id)
    tin = (
        (await db.execute(select(TinNhan).where(TinNhan.hoi_thoai_id == hoi_thoai_id).order_by(TinNhan.id).limit(500)))
        .scalars()
        .all()
    )
    dg_theo_tin: dict[int, list[DanhGiaCauTraLoi]] = defaultdict(list)
    if tin:
        for dg in (
            await db.execute(
                select(DanhGiaCauTraLoi)
                .where(DanhGiaCauTraLoi.tin_nhan_id.in_([t.id for t in tin]))
                .order_by(DanhGiaCauTraLoi.id)
            )
        ).scalars():
            dg_theo_tin[dg.tin_nhan_id].append(dg)
    return HoiThoaiAnDanhChiTiet(
        **tom.model_dump(),
        tin_nhan=[
            TinNhanAnDanh(
                id=t.id,
                vai_tro=t.vai_tro,
                noi_dung=che_thong_tin(t.noi_dung, ten),
                y_dinh=t.y_dinh,
                dau_hieu_nguy_hiem=t.dau_hieu_nguy_hiem,
                created_at=t.created_at,
                danh_gia=[
                    DanhGiaTinNhanRa(
                        nguon=dg.nguon,
                        ket_qua=dg.ket_qua,
                        ghi_chu=che_thong_tin(dg.ghi_chu, ten) if dg.ghi_chu else None,
                        cua_toi=nv is not None and dg.nguon == "duoc_si" and dg.nhan_vien_id == nv.id,
                    )
                    for dg in dg_theo_tin.get(t.id, [])
                ],
            )
            for t in tin
        ],
    )


# --- DS12 ---


async def ds_gan_co(db: AsyncSession, tp: ThamSoPhanTrang, *, chua_danh_gia: bool) -> Trang[HoiThoaiAnDanhTom]:
    """Hội thoại bị gắn cờ, mới nhất trước. `chua_danh_gia`: chưa có dược sĩ nào đánh giá tin nào."""
    stmt = _chon_tom().where(la_bi_gan_co())
    if chua_danh_gia:
        stmt = stmt.where(
            ~exists().where(
                TinNhan.hoi_thoai_id == HoiThoai.id,
                DanhGiaCauTraLoi.tin_nhan_id == TinNhan.id,
                DanhGiaCauTraLoi.nguon == "duoc_si",
            )
        )
    stmt = stmt.order_by(HoiThoai.created_at.desc(), HoiThoai.id.desc())
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return tao_trang(await _tom(db, dong), tong, tp)


async def chi_tiet_gan_co(db: AsyncSession, nv: NhanVien, hoi_thoai_id: int) -> HoiThoaiAnDanhChiTiet:
    return await _chi_tiet(db, hoi_thoai_id, nv, chi_gan_co=True)


async def danh_gia_tin_nhan(
    db: AsyncSession, nv: NhanVien, hoi_thoai_id: int, tin_nhan_id: int, vao: DanhGiaDuocSiVao
) -> HoiThoaiAnDanhChiTiet:
    """Dược sĩ đánh dấu một tin AI đúng/sai (kèm nội dung đúng); mỗi dược sĩ một đánh giá mỗi tin, gửi lại thì sửa."""
    await dam_bao_la_duoc_si(db, nv)
    gan_co = (
        await db.execute(select(HoiThoai.id).where(HoiThoai.id == hoi_thoai_id, la_bi_gan_co()).with_for_update())
    ).first()
    tin = await db.scalar(
        select(TinNhan.id).where(
            TinNhan.id == tin_nhan_id, TinNhan.hoi_thoai_id == hoi_thoai_id, TinNhan.vai_tro == VaiTroTinNhan.ai
        )
    )
    if gan_co is None or tin is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy câu trả lời cần đánh giá")
    ghi_chu = (vao.ghi_chu or "").strip() or None
    if vao.ket_qua == "sai" and (ghi_chu is None or len(ghi_chu) < TOI_THIEU_GHI_CHU_SAI):
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "ghi_chu", "loi": "Câu trả lời sai cần ghi nội dung đúng"}],
        )
    dg = await db.scalar(
        select(DanhGiaCauTraLoi).where(
            DanhGiaCauTraLoi.tin_nhan_id == tin_nhan_id,
            DanhGiaCauTraLoi.nguon == "duoc_si",
            DanhGiaCauTraLoi.nhan_vien_id == nv.id,
        )
    )
    if dg is None:
        dg = DanhGiaCauTraLoi(
            tin_nhan_id=tin_nhan_id, nguon="duoc_si", nhan_vien_id=nv.id, ket_qua=vao.ket_qua, ghi_chu=ghi_chu
        )
        db.add(dg)
    else:
        dg.ket_qua, dg.ghi_chu = vao.ket_qua, ghi_chu
    await db.flush()
    await ghi_nhat_ky(db, nhan_vien_id=nv.id, hanh_dong="danh_gia_ai", bang="danh_gia_cau_tra_loi", ban_ghi_id=dg.id)
    return await _chi_tiet(db, hoi_thoai_id, nv, chi_gan_co=True)


# --- AD11 ---


async def ds_giam_sat(
    db: AsyncSession,
    tp: ThamSoPhanTrang,
    *,
    tu_ngay: date | None,
    den_ngay: date | None,
    bi_gan_co: bool | None,
    da_chuyen_duoc_si: bool | None,
) -> Trang[HoiThoaiAnDanhTom]:
    _, _, dau, cuoi = _khoang(tu_ngay, den_ngay)
    stmt = _chon_tom().where(HoiThoai.created_at >= dau, HoiThoai.created_at < cuoi)
    if bi_gan_co is not None:
        stmt = stmt.where(la_bi_gan_co() if bi_gan_co else ~la_bi_gan_co())
    if da_chuyen_duoc_si is not None:
        stmt = stmt.where(
            HoiThoai.loai == LoaiHoiThoai.duoc_si if da_chuyen_duoc_si else HoiThoai.loai != LoaiHoiThoai.duoc_si
        )
    stmt = stmt.order_by(HoiThoai.created_at.desc(), HoiThoai.id.desc())
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return tao_trang(await _tom(db, dong), tong, tp)


async def chi_tiet_giam_sat(db: AsyncSession, hoi_thoai_id: int) -> HoiThoaiAnDanhChiTiet:
    return await _chi_tiet(db, hoi_thoai_id, None, chi_gan_co=False)


async def thong_ke(db: AsyncSession, *, tu_ngay: date | None, den_ngay: date | None) -> ThongKeAi:
    tu, den, dau, cuoi = _khoang(tu_ngay, den_ngay)
    trong = and_(HoiThoai.created_at >= dau, HoiThoai.created_at < cuoi)
    tong_ht, so_chuyen, so_gan_co, tong_token, chi_phi = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(HoiThoai.loai == LoaiHoiThoai.duoc_si),
                func.count().filter(la_bi_gan_co()),
                func.coalesce(func.sum(HoiThoai.tong_token), 0),
                func.coalesce(func.sum(HoiThoai.chi_phi), 0),
            ).where(trong)
        )
    ).one()
    pho_bien = (
        await db.execute(
            select(TinNhan.y_dinh, func.count().label("n"))
            .join(HoiThoai, HoiThoai.id == TinNhan.hoi_thoai_id)
            .where(trong, TinNhan.vai_tro == VaiTroTinNhan.khach, TinNhan.y_dinh.is_not(None))
            .group_by(TinNhan.y_dinh)
            .order_by(func.count().desc(), TinNhan.y_dinh)
            .limit(SO_CAU_HOI_PHO_BIEN)
        )
    ).all()
    dem_dg = dict(
        (
            await db.execute(
                select(func.concat(DanhGiaCauTraLoi.nguon, ":", DanhGiaCauTraLoi.ket_qua), func.count())
                .where(DanhGiaCauTraLoi.created_at >= dau, DanhGiaCauTraLoi.created_at < cuoi)
                .group_by(DanhGiaCauTraLoi.nguon, DanhGiaCauTraLoi.ket_qua)
            )
        ).all()
    )
    return ThongKeAi(
        tu_ngay=tu,
        den_ngay=den,
        tong_hoi_thoai=tong_ht,
        so_chuyen_duoc_si=so_chuyen,
        ty_le_chuyen_duoc_si=None
        if tong_ht == 0
        else (Decimal(so_chuyen) / Decimal(tong_ht)).quantize(Decimal("0.0001")),
        so_gan_co=so_gan_co,
        tong_token=int(tong_token),
        tong_chi_phi_usd=Decimal(chi_phi).quantize(Decimal("0.000001")),
        cau_hoi_pho_bien=[CauHoiPhoBien(y_dinh=y, so_luong=n) for y, n in pho_bien],
        danh_gia=ThongKeDanhGia(
            khach_huu_ich=dem_dg.get("khach:huu_ich", 0),
            khach_khong_huu_ich=dem_dg.get("khach:khong_huu_ich", 0),
            duoc_si_dung=dem_dg.get("duoc_si:dung", 0),
            duoc_si_sai=dem_dg.get("duoc_si:sai", 0),
        ),
    )


async def tim_kiem_khong_ket_qua(
    db: AsyncSession, *, tu_ngay: date | None, den_ngay: date | None
) -> list[TimKiemKhongKetQua]:
    """Từ khóa không ra kết quả, gộp không phân biệt hoa thường; cũng che SĐT/email (khách có thể gõ nhầm vào ô tìm)."""
    _, _, dau, cuoi = _khoang(tu_ngay, den_ngay)
    ten = func.lower(func.trim(LichSuTimKiem.tu_khoa))
    dong = (
        await db.execute(
            select(ten.label("tk"), func.count().label("n"), func.max(LichSuTimKiem.created_at).label("cuoi"))
            .where(LichSuTimKiem.so_ket_qua == 0, LichSuTimKiem.created_at >= dau, LichSuTimKiem.created_at < cuoi)
            .group_by(ten)
            .order_by(func.count().desc(), ten)
            .limit(SO_TU_KHOA_TOI_DA * 4)
        )
    ).all()
    gop: dict[str, list] = {}
    for tk, n, lan_cuoi in dong:
        che = che_thong_tin(tk)
        if che in gop:
            gop[che][0] += n
            gop[che][1] = max(gop[che][1], lan_cuoi)
        else:
            gop[che] = [n, lan_cuoi]
    xep = sorted(gop.items(), key=lambda kv: (-kv[1][0], kv[0]))[:SO_TU_KHOA_TOI_DA]
    return [TimKiemKhongKetQua(tu_khoa=tk, so_lan=n, lan_cuoi=c) for tk, (n, c) in xep]
