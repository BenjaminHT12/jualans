"""Tabel database Jualans.

users            daftar akun login (kata sandi disimpan sebagai hash PBKDF2, bukan teks asli)
sessions         token login yang aktif (yang disimpan hanya hash-nya)
categories       kategori uang masuk / uang keluar milik tiap pengguna
transactions     riwayat transaksi (uang masuk dan uang keluar)
customers        pelanggan yang punya bon
debt_items       rincian utang tiap pelanggan
stock_items      bahan yang dipantau stoknya
stock_history    riwayat perubahan stok
"""
import datetime as dt

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    contact: Mapped[str] = mapped_column(String(120), unique=True, index=True)   # no. HP / email yang sudah dinormalkan
    contact_display: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(200))
    business_name: Mapped[str] = mapped_column(String(80), default="")
    business_type: Mapped[str] = mapped_column(String(80), default="")
    setup_done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    sessions: Mapped[list["SessionToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class SessionToken(Base):
    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="sessions")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "type", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(10))          # masuk | keluar
    name: Mapped[str] = mapped_column(String(40))
    position: Mapped[int] = mapped_column(Integer, default=0)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_user_date", "user_id", "date"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(10))          # masuk | keluar
    item: Mapped[str] = mapped_column(String(200))
    amount: Mapped[int] = mapped_column(Integer)           # rupiah
    category: Mapped[str] = mapped_column(String(40))
    date: Mapped[dt.date] = mapped_column(Date)
    time: Mapped[str] = mapped_column(String(5))           # HH:MM
    source: Mapped[str] = mapped_column(String(20), default="manual")   # chat | form | scan | bon | ...
    scan_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    note: Mapped[str] = mapped_column(String(120), default="")

    items: Mapped[list["DebtItem"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan", order_by="DebtItem.date")


class DebtItem(Base):
    __tablename__ = "debt_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    desc: Mapped[str] = mapped_column(String(200))
    amount: Mapped[int] = mapped_column(Integer)
    date: Mapped[dt.date] = mapped_column(Date)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="items")


class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    unit: Mapped[str] = mapped_column(String(20))
    qty: Mapped[float] = mapped_column(Float, default=0)
    min: Mapped[float] = mapped_column(Float, default=0)
    keywords: Mapped[str] = mapped_column(Text, default="[]")   # JSON: kata kunci untuk mencocokkan belanjaan

    history: Mapped[list["StockHistory"]] = relationship(
        back_populates="stock_item", cascade="all, delete-orphan",
        order_by=lambda: [StockHistory.date.desc(), StockHistory.time.desc()])


class StockHistory(Base):
    __tablename__ = "stock_history"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    stock_item_id: Mapped[str] = mapped_column(ForeignKey("stock_items.id", ondelete="CASCADE"), index=True)
    date: Mapped[dt.date] = mapped_column(Date)
    time: Mapped[str] = mapped_column(String(5))
    change: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(String(160), default="")
    scan_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    stock_item: Mapped[StockItem] = relationship(back_populates="history")
