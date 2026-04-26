from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
import datetime


class Base(DeclarativeBase):
    pass


class Submission(Base):
    __tablename__ = "submissions"

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id:     Mapped[int]      = mapped_column(Integer, nullable=False)
    full_name:       Mapped[str]      = mapped_column(String(200), nullable=False)
    course:          Mapped[str]      = mapped_column(String(50), nullable=False)
    group:           Mapped[str]      = mapped_column(String(100), nullable=False)
    assignment_type: Mapped[str]      = mapped_column(String(50), nullable=False)
    topic:           Mapped[str]      = mapped_column(String(500), nullable=False)
    file_url:        Mapped[str]      = mapped_column(String(1000), nullable=True)
    score:           Mapped[int]      = mapped_column(Integer, nullable=True)
    grade:           Mapped[int]      = mapped_column(Integer, nullable=True)
    status:          Mapped[str]      = mapped_column(String(50), nullable=True)
    passed:          Mapped[str]      = mapped_column(String(10), nullable=True)
    created_at:      Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
