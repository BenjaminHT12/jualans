"""Akun demo dan data contoh usaha "Jualans" (cilok goreng) selama sekitar 3 bulan."""
import datetime as dt
import json
import random

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import Customer, DebtItem, StockHistory, StockItem, Transaction, User
from .services import create_default_categories, new_id, stock_keywords, today

# Akun demo untuk mencoba aplikasi (tombol "Masuk dengan akun demo" di halaman Login).
DEMO_CONTACT = "081234567890"
DEMO_PASSWORD = "jualans123"
DEMO_NAME = "Rina"
SAMPLE_DAYS = 100   # sedikit lebih dari 3 bulan, supaya terlihat bahwa riwayat dibatasi 90 hari


def ensure_demo_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.contact == DEMO_CONTACT))
    if user:
        return user
    user = User(id=new_id(), name=DEMO_NAME, contact=DEMO_CONTACT, contact_display="0812-3456-7890",
                password_hash=hash_password(DEMO_PASSWORD), business_name="Jualans",
                business_type="Cilok goreng", setup_done=True)
    db.add(user)
    db.flush()
    create_default_categories(db, user)
    seed_sample(db, user)
    db.commit()
    return user


def clear_user_data(db: Session, user: User) -> None:
    db.execute(delete(Transaction).where(Transaction.user_id == user.id))
    for c in db.scalars(select(Customer).where(Customer.user_id == user.id)).all():
        db.delete(c)
    for s in db.scalars(select(StockItem).where(StockItem.user_id == user.id)).all():
        db.delete(s)
    db.flush()


def _tx(user, day, time, type_, item, amount, category, source="chat"):
    return Transaction(id=new_id(), user_id=user.id, type=type_, item=item, amount=amount,
                       category=category, date=day, time=time, source=source)


def seed_sample(db: Session, user: User, days: int = SAMPLE_DAYS) -> None:
    rng = random.Random(7)
    t = today()
    rows = []
    for d in range(days - 1, -1, -1):
        day = t - dt.timedelta(days=d)
        weekend = day.weekday() >= 5
        if d == 0:   # hari ini baru setengah hari
            rows += [_tx(user, day, "07:05", "keluar", "Minyak goreng 2 liter", 36000, "Bahan baku"),
                     _tx(user, day, "11:30", "masuk", "Cilok goreng (18 porsi)", 90000, "Penjualan")]
            continue
        # belanja pagi
        if day.day == 1:
            rows.append(_tx(user, day, "06:45", "keluar", "Sewa lapak bulanan", 300000, "Sewa", "form"))
        if d % 3 == 0:
            rows.append(_tx(user, day, "07:10", "keluar", "Tepung tapioka 5 kg", 65000, "Bahan baku"))
        if d % 3 == 1:
            rows.append(_tx(user, day, "07:05", "keluar", "Minyak goreng 2 liter", 36000, "Bahan baku"))
        if d % 3 == 2:
            rows.append(_tx(user, day, "07:25", "keluar", "Gas elpiji 3 kg", 22000, "Operasional"))
        if d % 2 == 0:
            rows.append(_tx(user, day, "07:15", "keluar", "Daging ayam giling 1 kg", 48000, "Bahan baku"))
        if d % 4 == 0:
            rows.append(_tx(user, day, "07:30", "keluar", "Bumbu kacang & cabai", 30000, "Bahan baku"))
        if d % 7 == 3:
            rows.append(_tx(user, day, "08:10", "keluar", "Plastik & tusuk sate", 25000, "Operasional"))
        # penjualan sore
        porsi = rng.randint(18, 40) + (10 if weekend else 0)
        rows.append(_tx(user, day, f"17:{rng.randint(0, 45):02d}", "masuk", f"Cilok goreng ({porsi} porsi)", porsi * 5000, "Penjualan"))
        if rng.random() < 0.6:
            gelas = rng.randint(8, 22)
            rows.append(_tx(user, day, "17:50", "masuk", f"Es teh manis ({gelas} gelas)", gelas * 3000, "Penjualan"))
        if rng.random() < 0.08:
            porsi = rng.choice([30, 40, 50, 60])
            acara = rng.choice(["arisan Bu RT", "hajatan Pak Dedi", "pengajian RW 05", "ulang tahun Dika"])
            rows.append(_tx(user, day, "13:00", "masuk", f"Pesanan {acara} ({porsi} porsi)", porsi * 5000, "Pesanan"))
    db.add_all(rows)

    def debt(customer, days_ago, desc, amount):
        customer.items.append(DebtItem(id=new_id(), desc=desc, amount=amount, date=t - dt.timedelta(days=days_ago)))

    sri = Customer(id=new_id(), user_id=user.id, name="Bu Sri", note="Tetangga depan")
    debt(sri, 5, "Cilok goreng 4 porsi", 20000); debt(sri, 2, "Cilok goreng 3 porsi", 15000); debt(sri, 1, "Es teh manis 2 gelas", 6000)
    darto = Customer(id=new_id(), user_id=user.id, name="Pak Darto", note="Ojek pangkalan")
    debt(darto, 4, "Cilok goreng 2 porsi", 10000); debt(darto, 1, "Cilok goreng 3 porsi", 15000)
    rizki = Customer(id=new_id(), user_id=user.id, name="Mas Rizki", note="Anak kos")
    debt(rizki, 3, "Cilok goreng 4 porsi", 20000)
    db.add_all([sri, darto, rizki])

    def stock(name, unit, qty, min_, keywords, history):
        item = StockItem(id=new_id(), user_id=user.id, name=name, unit=unit, qty=qty, min=min_,
                         keywords=json.dumps(keywords or stock_keywords(name)))
        for days_ago, time, change, note in history:
            item.history.append(StockHistory(id=new_id(), date=t - dt.timedelta(days=days_ago), time=time, change=change, note=note))
        db.add(item)

    stock("Tepung tapioka", "kg", 7, 5, ["tepung", "tapioka", "aci"],
          [(0, "08:00", -2, "Dipakai"), (1, "08:00", -2, "Dipakai"), (3, "07:10", 5, "Belanja: Tepung tapioka 5 kg")])
    stock("Daging ayam giling", "kg", 0.5, 1, ["daging", "ayam"],
          [(0, "08:00", -0.5, "Dipakai"), (2, "07:15", 1, "Belanja: Daging ayam giling 1 kg")])
    stock("Minyak goreng", "liter", 3, 2, ["minyak"],
          [(0, "07:05", 2, "Belanja: Minyak goreng 2 liter"), (1, "17:00", -1, "Dipakai")])
    stock("Gas elpiji 3 kg", "tabung", 1, 1, ["gas", "elpiji", "lpg"], [(1, "07:25", 1, "Belanja: Gas elpiji 3 kg")])
    stock("Bumbu kacang", "kg", 1, 0.5, ["bumbu", "kacang"], [(1, "16:00", -0.5, "Dipakai"), (4, "07:30", 1.5, "Belanja: Bumbu kacang & cabai")])
    stock("Plastik kemasan", "pak", 3, 1, ["plastik", "kantong", "kemasan"], [(4, "08:10", 2, "Belanja: Plastik & tusuk sate")])
    stock("Tusuk sate", "pak", 0, 1, ["tusuk"], [(0, "09:00", -1, "Dipakai"), (4, "08:10", 1, "Belanja: Plastik & tusuk sate")])
    db.flush()
