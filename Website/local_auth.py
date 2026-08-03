"""
local_auth.py
Helper autentikasi lokal (MySQL + bcrypt) — pengganti firebase_auth.py.
Semua operasi berjalan offline tanpa ketergantungan cloud.
"""
import uuid
import bcrypt
from datetime import datetime

from extensions import db
from models import User, ParkingHistory


# ─── Password Hashing ────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash password menggunakan bcrypt."""
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(plain: str, hashed: str) -> bool:
    """Verifikasi password terhadap hash bcrypt."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


# ─── Auth: Sign In ───────────────────────────────────────────────────────────

def sign_in_with_username(username: str, password: str) -> User:
    """
    Login dengan username + password.
    Return objek User jika berhasil.
    Raise ValueError jika gagal.
    """
    user = User.query.filter_by(username=username).first()
    if not user:
        raise ValueError('Username tidak ditemukan.')
    if not check_password(password, user.password_hash):
        raise ValueError('Password salah.')
    return user


def sign_in_with_email(email: str, password: str) -> User:
    """
    Login dengan email + password (alternatif).
    Return objek User jika berhasil.
    Raise ValueError jika gagal.
    """
    user = User.query.filter_by(email=email).first()
    if not user:
        raise ValueError('Email tidak ditemukan.')
    if not check_password(password, user.password_hash):
        raise ValueError('Password salah.')
    return user


# ─── Auth: Create User ───────────────────────────────────────────────────────

def create_local_user(email: str, password: str, username: str = '',
                      nama: str = '', no_hp: str = '', role: str = 'user') -> str:
    """
    Buat user baru di MySQL.
    Return uid (UUID string) dari user baru.
    """
    # Cek duplikat email
    if User.query.filter_by(email=email).first():
        raise ValueError('EMAIL_EXISTS')
    # Cek duplikat username
    if username and User.query.filter_by(username=username).first():
        raise ValueError('USERNAME_EXISTS')

    uid = uuid.uuid4().hex  # 32 char hex string
    user = User(
        uid=uid,
        email=email,
        username=username,
        nama=nama,
        no_hp=no_hp,
        role=role,
        password_hash=hash_password(password),
    )
    db.session.add(user)
    db.session.commit()
    return uid


# ─── User Profile ────────────────────────────────────────────────────────────

def get_user_profile(uid: str) -> User | None:
    """Ambil objek User dari MySQL berdasarkan uid."""
    return User.query.get(uid)


def save_user_profile(uid: str, data: dict) -> None:
    """Update profil user di MySQL."""
    user = User.query.get(uid)
    if not user:
        return
    for key, val in data.items():
        if key == 'password_hash':
            continue  # jangan update password lewat sini
        if hasattr(user, key):
            setattr(user, key, val)
    db.session.commit()


# ─── Parking History ─────────────────────────────────────────────────────────

def get_parking_history() -> list:
    """
    Ambil semua parking_history dari MySQL, sorted by date ascending.
    Return list of dict: [{date, vehicle_count}, ...]
    """
    rows = ParkingHistory.query.order_by(ParkingHistory.date.asc()).all()
    return [
        {'date': row.date.strftime('%Y-%m-%d'), 'vehicle_count': row.vehicle_count}
        for row in rows
    ]


def save_parking_history(date_str: str, vehicle_count: int) -> None:
    """
    Simpan / update data parking_history di MySQL.
    Gunakan INSERT ... ON DUPLICATE KEY UPDATE via merge.
    """
    d = datetime.strptime(date_str, '%Y-%m-%d').date()
    existing = ParkingHistory.query.get(d)
    if existing:
        existing.vehicle_count = vehicle_count
    else:
        db.session.add(ParkingHistory(date=d, vehicle_count=vehicle_count))
    db.session.commit()
