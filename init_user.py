"""
init_user.py
Script untuk membuat user admin di MySQL lokal.
Jalankan SEKALI: python init_user.py
"""
import os, sys

# ── Pastikan app context tersedia ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from local_auth import create_local_user, hash_password
from models import User

ADMIN_EMAIL    = 'admin@smartparking.com'
ADMIN_PASSWORD = 'admin123'
ADMIN_USERNAME = 'admin'
ADMIN_NAMA     = 'Administrator'

with app.app_context():
    existing = User.query.filter_by(email=ADMIN_EMAIL).first()
    if existing:
        print(f"[INFO] User admin sudah ada: uid={existing.uid}")
    else:
        uid = create_local_user(
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
            username=ADMIN_USERNAME,
            nama=ADMIN_NAMA,
            role='admin',
        )
        print(f"[OK] User admin berhasil dibuat: uid={uid}")

    print(f"      Email   : {ADMIN_EMAIL}")
    print(f"      Password: {ADMIN_PASSWORD}")
    print(f"      Username: {ADMIN_USERNAME}")
