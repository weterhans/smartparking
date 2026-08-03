"""
models.py
SQLAlchemy ORM models untuk Smart Parking — MySQL/MariaDB lokal.
"""
from datetime import datetime, date
from extensions import db


class User(db.Model):
    """Tabel users — autentikasi & profil."""
    __tablename__ = 'users'

    uid           = db.Column(db.String(128), primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    username      = db.Column(db.String(100), nullable=False)
    nama          = db.Column(db.String(255), nullable=False)
    no_hp         = db.Column(db.String(20))
    role          = db.Column(db.String(50), default='user')
    password_hash = db.Column(db.String(255), nullable=False, default='')
    jenis_kelamin = db.Column(db.String(20), default='')
    tanggal_lahir = db.Column(db.Date, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Alias agar template lama yang pakai current_user.id tetap berjalan
    @property
    def id(self):
        return self.uid

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.uid


class ParkingSlot(db.Model):
    """Tabel parking_slots — status slot dari sensor IoT."""
    __tablename__ = 'parking_slots'

    id           = db.Column(db.String(50), primary_key=True)   # e.g. Slot_A1
    status       = db.Column(db.String(20), default='Tersedia')  # Tersedia / Terisi
    check_in     = db.Column(db.DateTime, nullable=True)
    vehicle_type = db.Column(db.String(20), default='Kecil')
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(db.Model):
    """Tabel subscriptions — data pelanggan berlangganan."""
    __tablename__ = 'subscriptions'

    id         = db.Column(db.String(50), primary_key=True)
    name       = db.Column(db.String(255), nullable=False)
    card_uid   = db.Column(db.String(100), unique=True)
    slot_id    = db.Column(db.String(50), db.ForeignKey('parking_slots.id'), nullable=True)
    status     = db.Column(db.String(20), default='active')
    expired_at = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ParkingHistory(db.Model):
    """Tabel parking_history — jumlah kendaraan harian (untuk prediksi)."""
    __tablename__ = 'parking_history'

    date          = db.Column(db.Date, primary_key=True)
    vehicle_count = db.Column(db.Integer, default=0)


class Transaction(db.Model):
    """Tabel transactions — catatan transaksi parkir."""
    __tablename__ = 'transactions'

    id                    = db.Column(db.String(100), primary_key=True)
    slot_id               = db.Column(db.String(50), db.ForeignKey('parking_slots.id'))
    user_identifier       = db.Column(db.String(100))
    transaction_date      = db.Column(db.Date)
    transaction_timestamp = db.Column(db.BigInteger)
    duration_hours        = db.Column(db.Integer)
    fee                   = db.Column(db.Numeric(10, 2))
    is_subscriber         = db.Column(db.Boolean, default=False)
    vehicle_type          = db.Column(db.String(20), default='Kecil')
