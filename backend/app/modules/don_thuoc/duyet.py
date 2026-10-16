"""Duyệt yêu cầu đơn thuốc (DS04) và tạo đơn từ đơn thuốc (DS05), T5.3. Không commit.

Chỉ yêu cầu ĐANG KHÓA CHO MÌNH mới xem/xử lý được. Hồ sơ sức khỏe của khách đi qua `duoc_doc_ho_so_suc_khoe` (spec 03
mục 5.1). Đơn tạo ra đi qua `khoi_tao_trang_thai` (dòng 3) và giữ hàng FEFO; thuốc kê đơn CHỈ vào đơn qua đường này.
"""

import hashlib
import logging
import secrets
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.cau_hinh import doc_cau_hinh
from app.core.config import settings
from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_don_hang
from app.core.phan_quyen import dam_bao_la_duoc_si
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtYeuCauDonThuoc, DonHang, YeuCauDonThuoc
from app.models.enums import KenhBan, MucDoTuongTac, TrangThaiDon, TrangThaiYeuCauDonThuoc
from app.models.he_thong import NhanVien
from app.models.san_pham import DonViQuyDoi, HoatChat, SanPham, ThanhPhan
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, khoi_tao_trang_thai, tac_nhan_tu_nhan_vien
from app.modules.chuyen_mon import canh_bao
from app.modules.cua_hang.hien_thi import ton_kha_dung
from app.modules.don_thuoc.schemas_duyet import (
    CanhBaoRa,
    CanhBaoVao,
    HangChoRa,
    SanPhamChon,
    TaoDonRa,
    TaoDonVao,
    ThuocTrenDonRa,
    TrungAnhRa,
    YeuCauDuyetRa,
)
from app.modules.gio_hang import dich_vu as dich_vu_gio
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import YeuCauGiu
from app.modules.suc_khoe import dich_vu as suc_khoe
from app.modules.thong_bao import service as thong_bao
from app.tich_hop.tin_nhan import KenhTinNhan, LoiGuiTinNhan
from app.tich_hop.tin_nhan.mau.don_thuoc import sms_link_xac_nhan, sms_tu_choi

logger = logging.getLogger(__name__)
TT = TrangThaiYeuCauDonThuoc
KHOA_MAC_DINH_PHUT = 30
MUC_CAN_GHI_CHU = (MucDoTuongTac.nghiem_trong, MucDoTuongTac.chong_chi_dinh)
MA_LOI_KHONG_KHOA = "Yêu cầu này không đang được khóa cho bạn. Hãy nhận xử lý trước"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _phut_khoa(db: AsyncSession) -> int:
    return int(await doc_cau_hinh(db, "thoi_gian_khoa_don_thuoc_phut", KHOA_MAC_DINH_PHUT))


async def _lay(db: AsyncSession, yc_id: int, *, khoa: bool = False) -> YeuCauDonThuoc:
    cau = select(YeuCauDonThuoc).where(YeuCauDonThuoc.id == yc_id)
    if khoa:
        cau = cau.with_for_update().execution_options(populate_existing=True)
    yc = (await db.execute(cau)).scalars().first()
    if yc is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy yêu cầu đơn thuốc")
    return yc


def _khoa_cho_toi(yc: YeuCauDonThuoc, nv: NhanVien) -> bool:
    return yc.trang_thai == TT.dang_tu_van and yc.duoc_si_id == nv.id


async def _lay_dang_khoa(db: AsyncSession, nv: NhanVien, yc_id: int, *, khoa: bool = False) -> YeuCauDonThuoc:
    await dam_bao_la_duoc_si(db, nv)  # lớp phòng thủ thứ hai: Admin gán quyền cho vai trò khác cũng không duyệt được
    yc = await _lay(db, yc_id, khoa=khoa)
    if not _khoa_cho_toi(yc, nv):
        raise LoiNghiepVu("KHONG_CO_QUYEN", MA_LOI_KHONG_KHOA)
    return yc


# --- Hàng chờ và khóa (DS04) ---


async def hang_cho(db: AsyncSession, nv: NhanVien) -> list[HangChoRa]:
    """Yêu cầu `cho_duyet` (mọi dược sĩ thấy) và yêu cầu `dang_tu_van` do chính mình khóa. Cũ nhất trước."""
    ds = (
        (
            await db.execute(
                select(YeuCauDonThuoc)
                .where(
                    YeuCauDonThuoc.kenh == KenhBan.online,
                    or_(
                        YeuCauDonThuoc.trang_thai == TT.cho_duyet,
                        (YeuCauDonThuoc.trang_thai == TT.dang_tu_van) & (YeuCauDonThuoc.duoc_si_id == nv.id),
                    ),
                )
                .order_by(YeuCauDonThuoc.created_at, YeuCauDonThuoc.id)
                .limit(200)
            )
        )
        .scalars()
        .all()
    )
    return [
        HangChoRa(
            id=y.id,
            ma_yeu_cau=y.ma_yeu_cau,
            ho_ten=y.ho_ten,
            so_dien_thoai=y.so_dien_thoai,
            trang_thai=y.trang_thai,
            so_anh=len(y.anh_don_thuoc or []),
            la_thanh_vien=y.khach_hang_id is not None,
            khoa_boi_toi=_khoa_cho_toi(y, nv),
            khoa_luc=y.khoa_luc,
            created_at=y.created_at,
        )
        for y in ds
    ]


async def nhan_xu_ly(db: AsyncSession, nv: NhanVien, yc_id: int) -> YeuCauDuyetRa:
    """Khóa yêu cầu cho dược sĩ (dòng 3). Người khác đã khóa thì `409`; nhận lại của mình thì gia hạn."""
    await dam_bao_la_duoc_si(db, nv)
    yc = await _lay(db, yc_id, khoa=True)
    if yc.trang_thai == TT.cho_duyet or _khoa_cho_toi(yc, nv):
        yc.trang_thai = TT.dang_tu_van
        yc.duoc_si_id = nv.id
        yc.khoa_luc = bay_gio_utc()
        yc.updated_at = yc.khoa_luc
        await db.flush()
        return await chi_tiet(db, nv, yc_id)
    if yc.trang_thai == TT.dang_tu_van:
        raise LoiNghiepVu("DA_CO_NGUOI_XU_LY", "Yêu cầu này đang được dược sĩ khác xử lý")
    raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Yêu cầu này không còn ở trạng thái chờ xử lý")


async def nha_khoa(db: AsyncSession, nv: NhanVien, yc_id: int) -> None:
    """Dược sĩ trả yêu cầu về hàng chờ (dòng 4 do chính người khóa thực hiện sớm)."""
    yc = await _lay_dang_khoa(db, nv, yc_id, khoa=True)
    if await _don_dang_hieu_luc(db, yc.id):
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Yêu cầu đang có đơn hàng chờ khách xác nhận")
    yc.trang_thai, yc.duoc_si_id, yc.khoa_luc, yc.updated_at = TT.cho_duyet, None, None, bay_gio_utc()


async def _don_dang_hieu_luc(db: AsyncSession, yc_id: int) -> bool:
    return bool(
        await db.scalar(
            select(func.count())
            .select_from(DonHang)
            .where(DonHang.yeu_cau_don_thuoc_id == yc_id, DonHang.trang_thai != TrangThaiDon.da_huy)
        )
    )


# --- Màn duyệt ---


async def chi_tiet(db: AsyncSession, nv: NhanVien, yc_id: int) -> YeuCauDuyetRa:
    yc = await _lay_dang_khoa(db, nv, yc_id)
    ct = (
        (await db.execute(select(CtYeuCauDonThuoc).where(CtYeuCauDonThuoc.yeu_cau_id == yc.id).order_by("id")))
        .scalars()
        .all()
    )
    trung = []
    if yc.hash_anh:
        trung = (
            (
                await db.execute(
                    select(YeuCauDonThuoc)
                    .where(YeuCauDonThuoc.hash_anh == yc.hash_anh, YeuCauDonThuoc.id != yc.id)
                    .order_by(YeuCauDonThuoc.created_at.desc())
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )
    ho_so = None
    if yc.khach_hang_id is not None and await suc_khoe.duoc_doc_ho_so_suc_khoe(db, nv, yc.khach_hang_id):
        ho_so = await suc_khoe.dung_ho_so(db, yc.khach_hang_id)
    phut = await _phut_khoa(db)
    return YeuCauDuyetRa(
        id=yc.id,
        ma_yeu_cau=yc.ma_yeu_cau,
        ho_ten=yc.ho_ten,
        so_dien_thoai=yc.so_dien_thoai,
        ghi_chu=yc.ghi_chu,
        trang_thai=yc.trang_thai,
        khoa_luc=yc.khoa_luc,
        het_khoa_luc=None if yc.khoa_luc is None else yc.khoa_luc + timedelta(minutes=phut),
        la_thanh_vien=yc.khach_hang_id is not None,
        anh=[luu_tru.url_ky(k) for k in yc.anh_don_thuoc or []],
        ket_qua_ai=yc.ket_qua_ai,
        thuoc_tren_don=[
            ThuocTrenDonRa(
                ten_thuoc_tren_don=c.ten_thuoc_tren_don,
                ham_luong=c.ham_luong,
                so_luong_ke=c.so_luong_ke,
                do_tin_cay_ai=c.do_tin_cay_ai,
                san_pham_id=c.san_pham_id,
            )
            for c in ct
        ],
        checklist=yc.checklist,
        trung_anh=[
            TrungAnhRa(
                ma_yeu_cau=t.ma_yeu_cau, trang_thai=t.trang_thai, da_su_dung=t.da_su_dung, created_at=t.created_at
            )
            for t in trung
        ],
        ho_so_suc_khoe=ho_so,
    )


async def tim_san_pham(db: AsyncSession, nv: NhanVien, yc_id: int, q: str) -> list[SanPhamChon]:
    """Gợi ý sản phẩm (kể cả thuốc kê đơn) kèm tồn khả dụng và đơn vị, tìm theo tên hoặc hoạt chất. Tối đa 20."""
    from sqlalchemy import exists

    from app.core.tim_kiem import mau_tim_like
    from app.models.enums import TrangThaiKinhDoanh

    await _lay_dang_khoa(db, nv, yc_id)
    q = q.strip()
    if not q:
        return []
    mau = func.unaccent(mau_tim_like(q))
    co_hoat_chat = exists().where(
        ThanhPhan.san_pham_id == SanPham.id,
        HoatChat.id == ThanhPhan.hoat_chat_id,
        func.unaccent(HoatChat.ten).ilike(mau, escape="\\"),
    )
    ds = (
        await db.execute(
            select(SanPham, ton_kha_dung().label("ton"))
            .where(
                SanPham.deleted_at.is_(None),
                SanPham.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh,
                func.unaccent(SanPham.ten).ilike(mau, escape="\\") | co_hoat_chat,
            )
            .order_by(SanPham.ten)
            .limit(20)
        )
    ).all()
    ids = [sp.id for sp, _ in ds]
    dv = {i: [] for i in ids}
    hc: dict[int, list[str]] = {i: [] for i in ids}
    if ids:
        for d in (
            (await db.execute(select(DonViQuyDoi).where(DonViQuyDoi.san_pham_id.in_(ids)).order_by("he_so", "id")))
            .scalars()
            .all()
        ):
            dv[d.san_pham_id].append(d)
        for sp_id, ten in (
            await db.execute(
                select(ThanhPhan.san_pham_id, HoatChat.ten)
                .join(HoatChat, HoatChat.id == ThanhPhan.hoat_chat_id)
                .where(ThanhPhan.san_pham_id.in_(ids))
                .order_by(HoatChat.ten)
            )
        ).all():
            hc[sp_id].append(ten)
    return [
        SanPhamChon(
            id=sp.id,
            ten=sp.ten,
            loai_san_pham=sp.loai_san_pham,
            don_vi_co_so=sp.don_vi_co_so,
            ton_kha_dung=max(int(ton or 0), 0),
            hoat_chat=hc[sp.id],
            don_vi=[
                {"id": d.id, "ten_don_vi": d.ten_don_vi, "he_so": d.he_so, "gia_ban": d.gia_ban} for d in dv[sp.id]
            ],
        )
        for sp, ton in ds
    ]


async def _canh_bao(db: AsyncSession, yc: YeuCauDonThuoc, sp_ids: list[int]) -> CanhBaoRa:
    tuong_tac = await canh_bao.kiem_tra_tuong_tac(db, sp_ids)
    di_ung = [] if yc.khach_hang_id is None else await canh_bao.kiem_tra_di_ung(db, yc.khach_hang_id, sp_ids)
    nang = any(c.muc_do in MUC_CAN_GHI_CHU for c in tuong_tac) or bool(di_ung)
    return CanhBaoRa(tuong_tac=tuong_tac, di_ung=di_ung, can_ghi_chu_tu_van=nang)


async def tinh_canh_bao(db: AsyncSession, nv: NhanVien, yc_id: int, vao: CanhBaoVao) -> CanhBaoRa:
    """Cảnh báo tương tác và dị ứng cho các dòng đang chọn; chỉ trả cảnh báo, không trả hồ sơ (spec 03 mục 5.1)."""
    yc = await _lay_dang_khoa(db, nv, yc_id)
    return await _canh_bao(db, yc, [d.san_pham_id for d in vao.dong])


async def tu_choi(db: AsyncSession, nv: NhanVien, yc_id: int, ly_do: str, kenh: KenhTinNhan) -> None:
    """Không hợp lệ (dòng 6): bắt buộc lý do, báo khách. Yêu cầu đã có đơn đang chờ thì không từ chối được."""
    yc = await _lay_dang_khoa(db, nv, yc_id, khoa=True)
    if await _don_dang_hieu_luc(db, yc.id):
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Yêu cầu đang có đơn hàng, hãy hủy đơn trước")
    yc.trang_thai, yc.ly_do_tu_choi, yc.updated_at = TT.tu_choi, ly_do.strip(), bay_gio_utc()
    if yc.khach_hang_id is not None:
        await thong_bao.gui_cho_khach(
            db,
            yc.khach_hang_id,
            loai="don_thuoc",
            tieu_de=f"Yêu cầu đơn thuốc {yc.ma_yeu_cau} chưa được chấp nhận",
            noi_dung=yc.ly_do_tu_choi,
            lien_ket="/tai-khoan/don-thuoc",
        )
    await _gui_sms(kenh, yc.so_dien_thoai, sms_tu_choi(yc.ma_yeu_cau, yc.ly_do_tu_choi[:100]))


async def _gui_sms(kenh: KenhTinNhan, sdt: str, noi_dung: str) -> None:
    try:
        await kenh.gui_sms(sdt, noi_dung)
    except LoiGuiTinNhan:  # SMS lỗi không làm hỏng nghiệp vụ; dược sĩ vẫn thấy link trong phản hồi
        logger.warning("Không gửi được SMS đơn thuốc", exc_info=True)


# --- Tạo đơn từ đơn thuốc (DS05) ---


def _thieu_checklist(vao: TaoDonVao) -> list[str]:
    return [k for k, v in vao.checklist.model_dump().items() if not v]


async def tao_don(db: AsyncSession, nv: NhanVien, yc_id: int, vao: TaoDonVao, kenh: KenhTinNhan) -> TaoDonRa:
    yc = await _lay_dang_khoa(db, nv, yc_id, khoa=True)
    if await _don_dang_hieu_luc(db, yc.id):
        raise LoiNghiepVu("TRUNG_DU_LIEU", "Yêu cầu này đã có đơn hàng đang hiệu lực")
    thieu = _thieu_checklist(vao)
    if thieu:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Cần hoàn thành đủ checklist trước khi tạo đơn",
            chi_tiet=[{"truong": f"checklist.{k}", "loi": "Chưa đạt"} for k in thieu],
        )
    da_dung = []
    if yc.hash_anh:
        da_dung = (
            (
                await db.execute(
                    select(YeuCauDonThuoc.ma_yeu_cau).where(
                        YeuCauDonThuoc.hash_anh == yc.hash_anh,
                        YeuCauDonThuoc.id != yc.id,
                        YeuCauDonThuoc.da_su_dung.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
    if da_dung and not vao.xac_nhan_trung_anh:
        raise LoiNghiepVu(
            "CAN_XAC_NHAN_CANH_BAO",
            "Ảnh đơn trùng với đơn đã được sử dụng. Hãy kiểm tra và xác nhận nếu vẫn chấp nhận",
            chi_tiet={"loai": "trung_anh", "ma_yeu_cau": list(da_dung)},
        )
    gop: dict[tuple[int, int], int] = {}
    for d in vao.dong:
        gop[(d.san_pham_id, d.don_vi_id)] = gop.get((d.san_pham_id, d.don_vi_id), 0) + d.so_luong
    dong_dat = await dich_vu_gio.kiem_tra_dong_de_dat(
        db, [(i, sp, dv, sl) for i, ((sp, dv), sl) in enumerate(gop.items())], cho_phep_ke_don=True
    )
    cb = await _canh_bao(db, yc, [d.sp.id for d in dong_dat])
    ghi_chu = (vao.ghi_chu_tu_van or "").strip() or None
    if cb.can_ghi_chu_tu_van and ghi_chu is None:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Có cảnh báo nghiêm trọng, bắt buộc nhập ghi chú tư vấn",
            chi_tiet=[{"truong": "ghi_chu_tu_van", "loi": "Bắt buộc nhập ghi chú tư vấn"}],
        )
    # Không mã giảm giá; thuốc kê đơn không được giảm giá (CLAUDE.md quy tắc 6). Phí ship tính khi khách chọn địa chỉ.
    t = await dat_hang.tinh_tien(db, yc.khach_hang_id, dong_dat, None, None, dung_luot=False)
    bay_gio = bay_gio_utc()
    gio = int(await doc_cau_hinh(db, "thoi_han_khach_xac_nhan_gio", 24))
    token = secrets.token_urlsafe(32) if yc.khach_hang_id is None else None
    don = DonHang(
        ma_don=await ma_don_hang(db),
        khach_hang_id=yc.khach_hang_id,
        kenh_ban=KenhBan.online,
        yeu_cau_don_thuoc_id=yc.id,
        token_truy_cap_hash=None if token is None else hash_token(token),
        tam_tinh=t.tam_tinh,
        giam_gia=t.giam,
        phi_van_chuyen=t.phi,
        tong_tien=t.tong_tien,
        ten_nguoi_nhan=yc.ho_ten,
        sdt_nguoi_nhan=yc.so_dien_thoai,
        ghi_chu=ghi_chu,
        han_xac_nhan=bay_gio + timedelta(hours=gio),
    )
    don.chi_tiet = dat_hang.dong_cua_don(t)
    tac_nhan = await tac_nhan_tu_nhan_vien(db, nv)
    ls = await khoi_tao_trang_thai(db, don, TrangThaiDon.cho_khach_xac_nhan, tac_nhan, NGUON_NGUOI_DUNG)
    thu_tu = sorted(don.chi_tiet, key=lambda c: c.id)
    await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(c.id, c.san_pham_id, c.so_luong * c.he_so) for c in thu_tu])
    yc.trang_thai = TT.da_tao_don
    yc.checklist = {**vao.checklist.model_dump(), "ghi_chu_tu_van": ghi_chu}
    yc.updated_at = bay_gio
    await db.refresh(ls)
    han = don.han_xac_nhan.astimezone().strftime("%H:%M %d/%m")
    link = None
    if token is not None:
        link = f"{settings.FRONTEND_URL.rstrip('/')}/xac-nhan-don/{token}"
        await _gui_sms(kenh, yc.so_dien_thoai, sms_link_xac_nhan(don.ma_don, link, han))
    else:
        assert yc.khach_hang_id is not None
        await thong_bao.gui_cho_khach(
            db,
            yc.khach_hang_id,
            loai="don_thuoc",
            tieu_de=f"Đơn {don.ma_don} từ đơn thuốc đã sẵn sàng, vui lòng xác nhận",
            lien_ket=f"/tai-khoan/don-hang/{don.ma_don}",
        )
    return TaoDonRa(don=dat_hang.don_ra(don, None, [ls]), lien_ket_xac_nhan=link)
