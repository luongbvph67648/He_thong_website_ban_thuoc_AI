from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Quy ước đặt tên giúp Alembic sinh tên ràng buộc ổn định. Index và unique composite được đặt tên tường minh
# trong từng model, vì quy ước theo "cột đầu tiên" dễ trùng tên khi một bảng có nhiều index bắt đầu cùng một cột.
QUY_UOC_TEN = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Gốc của mọi model. Model chỉ khai báo cấu trúc, không chứa logic nghiệp vụ (logic nằm ở service)."""

    metadata = MetaData(naming_convention=QUY_UOC_TEN)
