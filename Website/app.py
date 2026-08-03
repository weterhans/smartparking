import os
import uuid
import base64
from datetime import datetime, date, timedelta
from functools import wraps
from collections import defaultdict
from decimal import Decimal

import plotly.graph_objs as go  # type: ignore
import plotly.io as pio  # type: ignore
import numpy as np

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from werkzeug.utils import secure_filename

from config import Config
from extensions import db
from models import User, ParkingSlot, Subscription, ParkingHistory, Transaction
from local_auth import (
    sign_in_with_username,
    get_user_profile,
    save_user_profile,
    get_parking_history,
    save_parking_history,
)

# ─── App Init ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config.from_object(Config)

# ─── Database Init ────────────────────────────────────────────────────────────
db.init_app(app)

from sqlalchemy import text

with app.app_context():
    # Buat tabel antrean simulasi jika belum ada (Bisa dibaca lintas perangkat/Windows-Pi)
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS simulation_queue (
            id INT AUTO_INCREMENT PRIMARY KEY,
            slot_id VARCHAR(50),
            vehicle_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.session.commit()

# ─── Auth Helpers ─────────────────────────────────────────────────────────────

def get_current_user() -> User | None:
    """Ambil objek User dari session. Return None jika tidak login."""
    uid = session.get('user_uid')
    if not uid:
        return None
    return get_user_profile(uid)


def login_required(f):
    """Decorator pengganti @login_required Flask-Login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_uid'):
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        if get_current_user() is None:
            session.clear()
            flash('Sesi tidak valid, silakan login kembali.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─── Custom Jinja Filter & Context ────────────────────────────────────────────
@app.template_filter('b64encode')
def b64encode_filter(data):
    if data is None:
        return ''
    return base64.b64encode(data).decode('utf-8')


@app.context_processor
def inject_globals():
    return {
        'current_year': datetime.now().year,
        'current_user': get_current_user(),
    }


# ─── Helper ───────────────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── Auth Blueprint ───────────────────────────────────────────────────────────
from auth_routes import auth_bp
app.register_blueprint(auth_bp)


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    if session.get('user_uid'):
        return redirect(url_for('index'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_uid'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        try:
            user = sign_in_with_username(username, password)
            session['user_uid'] = user.uid
            session['user_email'] = user.email
            return redirect(url_for('index'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Login gagal: {e}', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─── Dashboard ────────────────────────────────────────────────────────────────
@app.route('/index')
@login_required
def index():
    # ── Slot data
    try:
        slots = ParkingSlot.query.all()
        # Dapatkan reserved slots
        subs = Subscription.query.filter_by(status='active').all()
        reserved_slots = {s.slot_id for s in subs if s.slot_id}

        count_occupied = 0
        count_maintenance = 0
        for s in slots:
            is_reserved = s.id in reserved_slots
            if s.status == 'Maintenance':
                count_maintenance += 1
            elif s.status in ('occupied', 'Terisi') or is_reserved:
                count_occupied += 1
        
        available = len(slots) - count_occupied - count_maintenance
        occupied = count_occupied
    except Exception:
        available = occupied = 0

    # ── Jumlah subscriber aktif
    try:
        subs_count = Subscription.query.filter_by(status='active').count()
    except Exception:
        subs_count = 0

    # ── Revenue bulan ini
    try:
        current_month_str = datetime.now().strftime('%Y-%m')
        first_day = datetime.now().replace(day=1).date()
        txs = Transaction.query.filter(Transaction.transaction_date >= first_day).all()
        revenue = sum(float(t.fee or 0) for t in txs)
    except Exception:
        revenue = 0

    return render_template('index.html',
                           available=available, occupied=occupied,
                           subs_count=subs_count, revenue=revenue)


# ─── Monitoring ───────────────────────────────────────────────────────────────
@app.route('/monitoring')
@login_required
def monitoring():
    STATUS_MAP = {'Terisi': 'occupied', 'Tersedia': 'available', 'Maintenance': 'maintenance'}

    # Auto-expire langganan yang sudah lewat
    auto_expire_subscriptions()

    # Ambil semua subscriber aktif yang punya slot
    try:
        active_subs = Subscription.query.filter_by(status='active').all()
        reserved_map = {s.slot_id: s for s in active_subs if s.slot_id}
    except Exception:
        reserved_map = {}

    slots = []
    for i in range(1, 7):
        slot_key = f'Slot_A{i}'
        slot_obj = ParkingSlot.query.get(slot_key)

        try:
            usage_count = Transaction.query.filter_by(slot_id=slot_key).count()
        except Exception:
            usage_count = 0

        if slot_obj:
            raw_status = slot_obj.status or 'Tersedia'
            normalized_status = STATUS_MAP.get(raw_status, raw_status)
            check_in_str = slot_obj.check_in.isoformat() if slot_obj.check_in else ''
        else:
            raw_status = 'Maintenance' if usage_count >= 70 else 'Tersedia'
            normalized_status = 'maintenance' if usage_count >= 70 else 'available'
            check_in_str = ''

        # Cek apakah slot ini di-reserve subscriber
        is_reserved = slot_key in reserved_map
        subscriber_name = reserved_map[slot_key].name if is_reserved else ''
        subscriber_card = reserved_map[slot_key].card_uid if is_reserved else ''
        
        subscriber_expiry = ''
        if is_reserved:
            if reserved_map[slot_key].expired_at:
                subscriber_expiry = reserved_map[slot_key].expired_at.strftime("%d-%m-%Y")
            else:
                subscriber_expiry = 'Tdk Terbatas'

        slots.append({
            'id': f'A{i}',
            'slot_key': slot_key,
            'status': normalized_status,
            'usage_count': usage_count,
            'check_in': check_in_str,
            'is_subscriber': is_reserved,
            'subscriber_name': subscriber_name,
            'subscriber_card': subscriber_card,
            'subscriber_expiry': subscriber_expiry,
            'user_id': '',
            'vehicle_type': getattr(slot_obj, 'vehicle_type', 'Kecil') if slot_obj else 'Kecil',
        })

    # Hitung summary: reserved = terisi, maintenance = terpisah
    count_occupied = 0
    count_maintenance = 0
    for s in slots:
        if s['status'] == 'maintenance':
            count_maintenance += 1
        elif s['status'] == 'occupied' or s['is_subscriber']:
            count_occupied += 1
    count_available = len(slots) - count_occupied - count_maintenance

    return render_template('monitoring.html',
                           slots=slots,
                           count_available=count_available,
                           count_occupied=count_occupied,
                           count_maintenance=count_maintenance)


@app.route('/monitoring-gate')
@login_required
def monitoring_gate():
    return render_template('monitoring_gate.html')


@app.route('/simulate_checkout_web/<slot_id>', methods=['POST'])
def simulate_checkout_web(slot_id):
    vehicle_type = request.form.get('vehicle_type', 'Kecil')
    try:
        slot_key = slot_id if slot_id.startswith('Slot_') else f'Slot_{slot_id}'
        # Masukkan ke database agar hardware controller di Raspberry Pi bisa membacanya
        db.session.execute(
            text("INSERT INTO simulation_queue (slot_id, vehicle_type) VALUES (:slot_id, :vehicle_type)"),
            {'slot_id': slot_key, 'vehicle_type': vehicle_type}
        )
        db.session.commit()
        flash(f'Simulasi checkout {slot_id} dikirim ke Hardware. Silakan tekan Push Button untuk menyelesaikan.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal mengirim simulasi ke hardware: {e}', 'danger')
        
    return redirect(url_for('monitoring'))

@app.route('/checkout/<slot_id>', methods=['POST'])
@login_required
def checkout(slot_id):
    try:
        slot_key = f'Slot_{slot_id}'
        slot_obj = ParkingSlot.query.get(slot_key)
        if not slot_obj or slot_obj.status not in ('occupied', 'Terisi'):
            flash(f'Slot {slot_id} tidak valid atau tidak terisi.', 'warning')
            return redirect(url_for('monitoring'))

        now = datetime.now()
        duration_hours = 0
        fee = 0
        user_id = 'Guest'
        is_subscriber = False
        vehicle_type = request.form.get('vehicle_type') or getattr(slot_obj, 'vehicle_type', 'Kecil') or 'Kecil'

        if slot_obj.check_in:
            try:
                delta = now - slot_obj.check_in
                duration_hours = max(1, int(delta.total_seconds() / 3600) + (1 if delta.total_seconds() % 3600 > 0 else 0))
            except:
                duration_hours = 1

        if not is_subscriber:
            # First hour 5000. Subsequent hours: 2000 for Kecil, 3000 for Besar
            if vehicle_type == 'Besar':
                fee = 5000 + (max(0, duration_hours - 1) * 3000)
            else:
                fee = 5000 + (max(0, duration_hours - 1) * 2000)

        # Update parking history untuk Prediksi
        history_record = ParkingHistory.query.get(now.date())
        if history_record:
            history_record.vehicle_count += 1
        else:
            db.session.add(ParkingHistory(date=now.date(), vehicle_count=1))

        # Buat transaksi
        tx_id = f"{uuid.uuid4().hex[:6].upper()}"
        tx = Transaction(
            id=tx_id,
            slot_id=slot_key,
            user_identifier=user_id,
            transaction_date=now.date(),
            transaction_timestamp=int(now.timestamp()),
            duration_hours=duration_hours,
            fee=Decimal(fee),
            is_subscriber=is_subscriber,
            vehicle_type=vehicle_type,
        )
        db.session.add(tx)

        # Bebaskan slot
        slot_obj.status = 'Tersedia'
        slot_obj.check_in = None
        db.session.commit()

        # Auto-maintenance: if transaction count becomes multiple of 70
        usage_count = Transaction.query.filter_by(slot_id=slot_key).count()
        if usage_count > 0 and usage_count % 70 == 0:
            slot_obj.status = 'Maintenance'
            db.session.commit()

        flash(f'Checkout berhasil untuk slot {slot_id}. Biaya: Rp {fee:,}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal checkout: {e}', 'danger')

    return redirect(url_for('monitoring'))


@app.route('/maintenance_done/<slot_id>', methods=['POST'])
@login_required
def maintenance_done(slot_id):
    try:
        slot_key = f'Slot_{slot_id}'
        slot_obj = ParkingSlot.query.get(slot_key)
        if slot_obj and slot_obj.status == 'Maintenance':
            slot_obj.status = 'Tersedia'
            db.session.commit()
            flash(f'Maintenance slot {slot_id} telah selesai.', 'success')
        else:
            flash(f'Slot {slot_id} tidak sedang maintenance.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menyelesaikan maintenance: {e}', 'danger')

    return redirect(url_for('monitoring'))

# ─── Constants ────────────────────────────────────────────────────────────────
TARIFF_PER_HOUR = 3000
AVAILABLE_CARDS = ['832B3434', '3A5D0307', 'C10E0407']
DURATION_OPTIONS = [
    {'value': '1w',  'label': '1 Minggu',  'days': 7,   'price': 75000},
    {'value': '2w',  'label': '2 Minggu',  'days': 14,  'price': 140000},
    {'value': '1m',  'label': '1 Bulan',   'days': 30,  'price': 250000},
    {'value': '2m',  'label': '2 Bulan',   'days': 60,  'price': 460000},
    {'value': '3m',  'label': '3 Bulan',   'days': 90,  'price': 650000},
    {'value': '6m',  'label': '6 Bulan',   'days': 180, 'price': 1100000},
    {'value': '1y',  'label': '1 Tahun',   'days': 365, 'price': 1950000},
]


def auto_expire_subscriptions():
    """Otomatis menangani langganan yang sudah expired."""
    today = date.today()
    try:
        expired = Subscription.query.filter(
            Subscription.expired_at != None,
            Subscription.expired_at < today,
            Subscription.status == 'active'
        ).all()
        for sub in expired:
            # Cek apakah mobil masih ada di dalam (slot Terisi)
            slot_obj = None
            if sub.slot_id:
                slot_obj = ParkingSlot.query.get(sub.slot_id)
                
            if slot_obj and slot_obj.status in ('occupied', 'Terisi'):
                # Ubah jadi kendaraan reguler yang masuk jam 00:00 hari ini
                midnight = datetime.combine(today, datetime.min.time())
                slot_obj.check_in = midnight
                
                # Lepaskan ikatan slot dari pelanggan ini
                sub.slot_id = None
            
            # Nonaktifkan kartu pelanggan
            if sub.card_uid in ['832B3434', '3A5D0307', 'C10E0407']:
                sub.name = ''
                sub.slot_id = None
                sub.expired_at = None
                sub.status = 'inactive'
            else:
                db.session.delete(sub)
                
        if expired:
            db.session.commit()
    except Exception:
        db.session.rollback()

@app.route('/finance')
@login_required
def finance():
    sort_order = request.args.get('sort', 'newest')
    limit_val = request.args.get('limit', '50')
    
    try:
        limit_num = int(limit_val)
    except ValueError:
        limit_num = 50

    try:
        raw_txs = Transaction.query.all()
    except Exception:
        raw_txs = []

    transactions = []
    total_revenue = 0

    current_month_str = datetime.now().strftime('%Y-%m')
    current_month_count = 0
    months_data = defaultdict(lambda: {'count': 0, 'total': 0})

    for t in raw_txs:
        fee = float(t.fee or 0)
        date_str = t.transaction_date.strftime('%Y-%m-%d') if t.transaction_date else ''
        ts = t.transaction_timestamp or 0
        hrs = t.duration_hours or 0
        sid = t.slot_id or '-'
        uid = t.user_identifier or '-'
        sub = t.is_subscriber or False
        vtype = t.vehicle_type or 'Kecil'

        # Hitung waktu masuk dari timestamp
        if ts:
            ci_dt = datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else None
            check_out_str = ci_dt.strftime('%H:%M') if ci_dt else '-'
            if ci_dt and hrs:
                check_in_dt = ci_dt - timedelta(hours=hrs)
                check_in_str = check_in_dt.strftime('%H:%M')
            else:
                check_in_str = '-'
        else:
            check_in_str = '-'
            check_out_str = '-'

        total_revenue += fee

        if date_str.startswith(current_month_str):
            current_month_count += 1

        if len(date_str) >= 7:
            ym = date_str[:7]
            months_data[ym]['count'] += 1
            months_data[ym]['total'] += fee

        if vtype == 'Besar':
            display_tariff = 3000
        else:
            display_tariff = 2000

        transactions.append({
            'id':             t.id,
            'date':           date_str,
            'slot_id':        sid,
            'user_id':        uid,
            'check_in':       check_in_str,
            'check_out':      check_out_str,
            'duration_hours': hrs,
            'tariff':         display_tariff,
            'fee':            fee,
            'is_subscriber':  sub,
            'ts':             ts,
            'vehicle_type':   vtype,
        })

    if sort_order == 'oldest':
        transactions.sort(key=lambda x: x.get('ts', 0), reverse=False)
    else:
        transactions.sort(key=lambda x: x.get('ts', 0), reverse=True)
        
    if limit_num > 0:
        display_transactions = transactions[:limit_num]
    else:
        display_transactions = transactions

    monthly_summary = []
    month_names = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    for ym in sorted(months_data.keys(), reverse=True):
        year, month = ym.split('-')
        month_idx = int(month)
        month_name = month_names[month_idx] if 1 <= month_idx <= 12 else month
        monthly_summary.append({
            'month': month_name,
            'year': year,
            'count': months_data[ym]['count'],
            'total': months_data[ym]['total']
        })

    return render_template('Finance.html',
                           transactions=display_transactions,
                           total_revenue=total_revenue,
                           tariff=TARIFF_PER_HOUR,
                           current_month_count=current_month_count,
                           monthly_summary=monthly_summary,
                           current_sort=sort_order,
                           current_limit=limit_val)


@app.route('/finance/add', methods=['POST'])
@login_required
def finance_add():
    """Input transaksi/pembayaran manual."""
    try:
        slot_id       = request.form.get('slot_id', '').strip()
        user_id       = request.form.get('user_id', 'Guest').strip() or 'Guest'
        date_str      = request.form.get('date', '').strip()
        
        dur_str       = request.form.get('duration_hours', '').strip()
        duration      = int(dur_str) if dur_str.isdigit() else 1
        
        vehicle_type  = request.form.get('vehicle_type', 'Kecil')
        is_sub        = request.form.get('is_subscriber') == 'on'

        # Validasi
        if not slot_id or not date_str:
            flash('Slot dan Tanggal wajib diisi.', 'danger')
            return redirect(url_for('finance'))

        tx_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        if is_sub:
            fee = 0
        elif vehicle_type == 'Besar':
            fee = 5000 + max(0, duration) * 3000
        else:
            fee = 5000 + max(0, duration) * 2000

        # Pastikan slot parkir ada di tabel parking_slots untuk menghindari error Foreign Key
        slot_obj = ParkingSlot.query.get(slot_id)
        if not slot_obj:
            slot_obj = ParkingSlot(id=slot_id, status='Tersedia', check_in=datetime.now())
            db.session.add(slot_obj)
            db.session.flush()

        tx_id = f"{uuid.uuid4().hex[:6].upper()}"
        tx = Transaction(
            id=tx_id,
            slot_id=slot_id,
            user_identifier=user_id,
            transaction_date=tx_date,
            transaction_timestamp=int(datetime.combine(tx_date, datetime.min.time()).timestamp()),
            duration_hours=duration,
            fee=Decimal(fee),
            is_subscriber=is_sub,
            vehicle_type=vehicle_type,
        )
        db.session.add(tx)
        
        # Update parking history untuk Prediksi
        history_record = ParkingHistory.query.get(tx_date)
        if history_record:
            history_record.vehicle_count += 1
        else:
            db.session.add(ParkingHistory(date=tx_date, vehicle_count=1))
            
        db.session.commit()
        flash(f'Transaksi berhasil ditambahkan! ID: {tx_id}, Biaya: Rp {fee:,}', 'success')
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        db.session.rollback()
        print("TRANSACTION ADD ERROR:", err_detail)
        flash(f'Gagal menambahkan transaksi: {e}. Cek terminal untuk detail (atau kirimkan pesan ini ke asisten).', 'danger')
    return redirect(url_for('finance'))


@app.route('/finance/delete/<string:tx_id>', methods=['POST'])
@login_required
def finance_delete(tx_id):
    """Hapus transaksi dari history."""
    try:
        tx = Transaction.query.get(tx_id)
        if tx:
            db.session.delete(tx)
            db.session.commit()
            flash('Transaksi berhasil dihapus!', 'success')
        else:
            flash('Transaksi tidak ditemukan.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus transaksi: {e}', 'danger')
    return redirect(url_for('finance'))


@app.route('/simulate_checkin/<slot_id>', methods=['POST'])
@login_required
def simulate_checkin(slot_id):
    """Simulasi kendaraan masuk manual via web."""
    try:
        slot_key = slot_id if slot_id.startswith('Slot_') else f'Slot_{slot_id}'
        vehicle_type = request.form.get('vehicle_type', 'Kecil')
        slot_obj = ParkingSlot.query.get(slot_key)
        if not slot_obj:
            slot_obj = ParkingSlot(id=slot_key, status='Terisi', check_in=datetime.now(), vehicle_type=vehicle_type)
            db.session.add(slot_obj)
        else:
            slot_obj.status = 'Terisi'
            slot_obj.check_in = datetime.now()
            slot_obj.vehicle_type = vehicle_type
        db.session.commit()
        flash(f'Simulasi kendaraan masuk berhasil di {slot_id}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal simulasi masuk: {e}', 'danger')
    return redirect(url_for('monitoring'))


# ─── Subscription ─────────────────────────────────────────────────────────────
@app.route('/subscription', methods=['GET'])
@login_required
def subscription():
    # Auto-expire langganan yang sudah lewat
    auto_expire_subscriptions()

    try:
        subs = Subscription.query.all()
    except Exception:
        subs = []
    subscribers = [{
        'id': s.id,
        'name': s.name,
        'card_uid': s.card_uid,
        'slot_id': s.slot_id or '',
        'status': s.status,
        'expired_at': s.expired_at.strftime('%Y-%m-%d') if s.expired_at else '',
    } for s in subs]

    # Slot yang sudah di-reserve subscriber aktif
    reserved_slots = {
        s.slot_id for s in subs if s.status == 'active' and s.slot_id
    }
    # Card UID yang sudah digunakan subscriber (aktif saja)
    used_cards = {
        s.card_uid for s in subs if s.card_uid and s.status == 'active'
    }
    # Jumlah ID card tersedia (belum digunakan subscriber aktif)
    available_cards_count = len(AVAILABLE_CARDS) - len(used_cards)

    # Daftar semua slot (A1-A6)
    all_slots = [f'Slot_A{i}' for i in range(1, 7)]

    return render_template('subscription.html',
                           subscribers=subscribers,
                           all_slots=all_slots,
                           reserved_slots=reserved_slots,
                           used_cards=used_cards,
                           available_cards=AVAILABLE_CARDS,
                           available_cards_count=available_cards_count,
                           duration_options=DURATION_OPTIONS)


@app.route('/subscription/add', methods=['POST'])
@login_required
def subscription_add():
    name = request.form.get('name', '').strip()
    card_uid = request.form.get('card_uid', '').strip()
    slot_id = request.form.get('slot_id', '').strip() or None
    duration = request.form.get('duration', '1m').strip()

    # Hitung expired_at dan harga dari durasi
    duration_days = 30  # default 1 bulan
    price = 250000
    for opt in DURATION_OPTIONS:
        if opt['value'] == duration:
            duration_days = opt['days']
            price = opt['price']
            break
    expired_at = date.today() + timedelta(days=duration_days)

    # Card UID sekarang bisa dari daftar yang tersedia atau diketik manual.
    # Tidak perlu memvalidasi apakah ada di AVAILABLE_CARDS.

    # Validasi: card_uid belum digunakan subscriber aktif lain
    existing_card = Subscription.query.filter_by(card_uid=card_uid, status='active').first()
    if existing_card:
        flash(f'Card UID {card_uid} sudah digunakan oleh subscriber aktif lain.', 'danger')
        return redirect(url_for('subscription'))

    # Validasi: slot belum di-reserve subscriber aktif lain
    if slot_id:
        existing_slot = Subscription.query.filter_by(slot_id=slot_id, status='active').first()
        if existing_slot:
            flash(f'Slot {slot_id} sudah di-reserve oleh subscriber lain.', 'danger')
            return redirect(url_for('subscription'))

    sub_id = f'SUB_{uuid.uuid4().hex[:8]}'
    data = Subscription(
        id=sub_id,
        name=name,
        card_uid=card_uid,
        slot_id=slot_id,
        status='active',
        expired_at=expired_at,
        created_at=datetime.now(),
    )
    try:
        db.session.add(data)
        
        # Tambahkan transaksi ke history finance
        now = datetime.now()
        tx_id = f"SUB-{uuid.uuid4().hex[:4].upper()}"
        tx = Transaction(
            id=tx_id,
            slot_id=slot_id,
            user_identifier=name,
            transaction_date=now.date(),
            transaction_timestamp=int(now.timestamp()),
            duration_hours=0,
            fee=Decimal(price),
            is_subscriber=True,
            vehicle_type='Langganan'
        )
        db.session.add(tx)
        
        db.session.commit()
        flash(f'Subscriber berhasil ditambahkan! Berlaku hingga {expired_at.strftime("%d %B %Y")}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menambahkan: {e}', 'danger')
    return redirect(url_for('subscription'))


@app.route('/subscription/edit/<string:sub_id>', methods=['POST'])
@login_required
def subscription_edit(sub_id):
    try:
        sub = Subscription.query.get(sub_id)
        if sub:
            new_card = request.form.get('card_uid', sub.card_uid).strip()
            new_slot = request.form.get('slot_id', '').strip() or None
            new_status = request.form.get('status', sub.status)
            new_duration = request.form.get('duration', '').strip()

            # Jika durasi dipilih ulang, hitung expired_at baru dari hari ini
            if new_duration:
                for opt in DURATION_OPTIONS:
                    if opt['value'] == new_duration:
                        sub.expired_at = date.today() + timedelta(days=opt['days'])
                        
                        # Tambahkan ke finance revenue untuk perpanjangan langganan
                        now = datetime.now()
                        tx_id = f"SUB-{uuid.uuid4().hex[:4].upper()}"
                        tx = Transaction(
                            id=tx_id,
                            slot_id=sub.slot_id,
                            user_identifier=sub.name,
                            transaction_date=now.date(),
                            transaction_timestamp=int(now.timestamp()),
                            duration_hours=0,
                            fee=Decimal(opt['price']),
                            is_subscriber=True,
                            vehicle_type='Langganan'
                        )
                        db.session.add(tx)
                        break

            # Card UID sekarang bebas dimasukkan (bisa dari daftar atau baru)

            # Validasi card_uid: belum digunakan subscriber aktif LAIN
            existing_card = Subscription.query.filter(
                Subscription.card_uid == new_card,
                Subscription.status == 'active',
                Subscription.id != sub_id
            ).first()
            if existing_card:
                flash(f'Card UID {new_card} sudah digunakan oleh subscriber lain.', 'danger')
                return redirect(url_for('subscription'))

            # Validasi slot: belum di-reserve subscriber aktif LAIN
            if new_slot and new_status == 'active':
                existing_slot = Subscription.query.filter(
                    Subscription.slot_id == new_slot,
                    Subscription.status == 'active',
                    Subscription.id != sub_id
                ).first()
                if existing_slot:
                    flash(f'Slot {new_slot} sudah di-reserve oleh subscriber lain.', 'danger')
                    return redirect(url_for('subscription'))

            sub.name = request.form.get('name', sub.name)
            sub.card_uid = new_card
            sub.slot_id = new_slot
            sub.status = new_status
            db.session.commit()
            flash('Data subscriber berhasil diperbarui!', 'success')
        else:
            flash('Subscriber tidak ditemukan.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal memperbarui: {e}', 'danger')
    return redirect(url_for('subscription'))


@app.route('/subscription/delete/<string:sub_id>', methods=['POST'])
@login_required
def subscription_delete(sub_id):
    try:
        sub = Subscription.query.get(sub_id)
        if sub:
            if sub.card_uid in ['832B3434', '3A5D0307', 'C10E0407']:
                sub.name = ''
                sub.slot_id = None
                sub.expired_at = None
                sub.status = 'inactive'
                db.session.commit()
                flash(f'Kartu langganan bawaan ({sub.card_uid}) berhasil dikosongkan dan siap digunakan ulang.', 'success')
            else:
                db.session.delete(sub)
                db.session.commit()
                flash('Subscriber berhasil dihapus!', 'success')
        else:
            flash('Subscriber tidak ditemukan.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus: {e}', 'danger')
    return redirect(url_for('subscription'))


# ─── Prediction ───────────────────────────────────────────────────────────────
@app.route('/prediction')
@login_required
def prediction():
    """Ambil data parking_history dari MySQL."""
    history_raw = get_parking_history()  # list of {date: str, vehicle_count: int}

    chart_daily_html  = ''
    chart_weekly_html = ''
    pred_summary      = {}

    # Parse tanggal
    parsed = []
    formatted_history = []
    for h in history_raw:
        try:
            if isinstance(h, dict) and 'date' in h:
                d = datetime.strptime(h['date'], '%Y-%m-%d').date()
                vc = int(h.get('vehicle_count', 0))
                parsed.append((d, vc))
                formatted_history.append({'date': d, 'vehicle_count': vc})
        except Exception:
            continue
    parsed.sort(key=lambda x: x[0])

    if len(parsed) >= 3:
        dates_ord   = [d.toordinal() for d, _ in parsed]
        counts      = [c for _, c in parsed]
        date_labels = [d.strftime('%Y-%m-%d') for d, _ in parsed]
        last_date   = parsed[-1][0]

        x = np.array(dates_ord, dtype=float)
        y = np.array(counts,    dtype=float)
        # Regresi penuh menggunakan semua data untuk memprediksi masa depan
        slope, intercept = np.polyfit(x, y, 1)

        # Prediksi 14 hari ke depan
        future_dates     = [last_date + timedelta(days=i + 1) for i in range(14)]
        future_predicted = [max(0, int(round(slope * d.toordinal() + intercept))) for d in future_dates]

        # Prediksi historis (rolling out-of-sample)
        # Mulai dari index 2 (hari ke-3) sebagai titik pangkal agar garis tersambung
        all_labels = [date_labels[2]]
        all_predicted = [counts[2]]
        
        for i in range(3, len(x)):
            x_train = x[:i]
            y_train = y[:i]
            s_i, inc_i = np.polyfit(x_train, y_train, 1)
            pred_val = max(0, int(round(s_i * x[i] + inc_i)))
            all_labels.append(date_labels[i])
            all_predicted.append(pred_val)
            
        # Gabungkan dengan masa depan
        all_labels.extend([d.strftime('%Y-%m-%d') for d in future_dates])
        all_predicted.extend(future_predicted)

        # Daily chart
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Scatter(
            x=date_labels, y=counts,
            mode='lines+markers', name='Data Aktual (Y)',
            line=dict(color='#0984e3', width=2)
        ))
        fig_daily.add_trace(go.Scatter(
            x=all_labels, y=all_predicted,
            mode='lines', name='Garis Prediksi (a + bX)',
            line=dict(color='#e74c3c', width=2, dash='dash')
        ))
        min_y_daily = min(min(counts) if counts else 0, min(all_predicted) if all_predicted else 0)
        max_y_daily = max(max(counts) if counts else 0, max(all_predicted) if all_predicted else 0)
        
        y_range_daily = [max(0, min_y_daily - 1), max_y_daily + 1]
        range_span_daily = y_range_daily[1] - y_range_daily[0]
        dtick_daily = max(1, int(range_span_daily / 5))

        fig_daily.update_layout(
            xaxis_title='Tanggal (X)', yaxis_title='Jumlah Kendaraan (Y)',
            yaxis=dict(tickformat="d", dtick=dtick_daily, range=y_range_daily),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(color='white'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        chart_daily_html = pio.to_html(fig_daily, full_html=False, include_plotlyjs=True,
                                       config={'responsive': True})

        # Weekly summary
        month_names_indo = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        weekly_groups = defaultdict(list)
        
        for d, c in parsed:
            # Mengelompokkan berdasarkan Senin-Minggu (1 Minggu penuh)
            monday = d - timedelta(days=d.weekday())
            sunday = monday + timedelta(days=6)
            key = (monday, sunday)
            weekly_groups[key].append(c)

        valid_week_keys = []
        max_date = max([d for d, c in parsed]) if parsed else None

        for k in sorted(weekly_groups.keys()):
            monday, sunday = k
            # Valid jika sudah 7 hari penuh ATAU minggu sudah terlewati oleh waktu berjalan
            if len(weekly_groups[k]) >= 7 or (max_date and max_date > sunday):
                valid_week_keys.append(k)

        week_labels = []
        for monday, sunday in valid_week_keys:
            m1 = month_names_indo[monday.month][:3]
            m2 = month_names_indo[sunday.month][:3]
            if monday.month == sunday.month:
                label = f"{monday.day}-{sunday.day} {m1}"
            else:
                label = f"{monday.day} {m1} - {sunday.day} {m2}"
            week_labels.append(label)

        week_totals = [sum(weekly_groups[k]) for k in valid_week_keys]

        if len(valid_week_keys) >= 2:
            wx = np.arange(len(valid_week_keys), dtype=float)
            wy = np.array(week_totals, dtype=float)
            # Regresi penuh untuk masa depan
            wslope, wintercept = np.polyfit(wx, wy, 1)
            future_week_totals = [max(0, int(round(wslope * (len(valid_week_keys) + i) + wintercept))) for i in range(4)]
            
            curr_monday, curr_sunday = valid_week_keys[-1]
            future_week_labels = []
            for _ in range(4):
                curr_monday += timedelta(days=7)
                curr_sunday += timedelta(days=7)
                m1 = month_names_indo[curr_monday.month][:3]
                m2 = month_names_indo[curr_sunday.month][:3]
                if curr_monday.month == curr_sunday.month:
                    label = f"{curr_monday.day}-{curr_sunday.day} {m1}"
                else:
                    label = f"{curr_monday.day} {m1} - {curr_sunday.day} {m2}"
                future_week_labels.append(label)

            # Prediksi historis mingguan (rolling out-of-sample)
            # Mulai dari index 1 (minggu ke-2) sebagai titik pangkal
            all_week_labels = [week_labels[1]]
            all_week_predicted = [week_totals[1]]
            
            for i in range(2, len(wx)):
                wx_train = wx[:i]
                wy_train = wy[:i]
                ws_i, winc_i = np.polyfit(wx_train, wy_train, 1)
                pred_val = max(0, int(round(ws_i * wx[i] + winc_i)))
                all_week_labels.append(week_labels[i])
                all_week_predicted.append(pred_val)
                
            all_week_labels.extend(future_week_labels)
            all_week_predicted.extend(future_week_totals)
        else:
            future_week_totals = []
            future_week_labels = []
            all_week_labels = []
            all_week_predicted = []

        if week_labels:
            fig_weekly = go.Figure()
            fig_weekly.add_trace(go.Scatter(
                x=week_labels, y=week_totals,
                mode='lines+markers', name='Data Aktual (Y)',
                line=dict(color='#0984e3', width=2)
            ))
            if len(valid_week_keys) >= 2:
                fig_weekly.add_trace(go.Scatter(
                    x=all_week_labels, y=all_week_predicted,
                    mode='lines', name='Garis Prediksi (a + bX)',
                    line=dict(color='#e74c3c', width=2, dash='dash')
                ))
            min_y_weekly = min(min(week_totals) if week_totals else 0, min(all_week_predicted) if all_week_predicted else 0)
            max_y_weekly = max(max(week_totals) if week_totals else 0, max(all_week_predicted) if all_week_predicted else 0)
            
            y_range_weekly = [max(0, min_y_weekly - 1), max_y_weekly + 1]
            range_span_weekly = y_range_weekly[1] - y_range_weekly[0]
            dtick_weekly = max(1, int(range_span_weekly / 5))
            
            fig_weekly.update_layout(
                xaxis_title='Bulan & Minggu', yaxis_title='Total Kendaraan',
                yaxis=dict(tickformat="d", dtick=dtick_weekly, range=y_range_weekly),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=40, b=20),
                font=dict(color='white'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            chart_weekly_html = pio.to_html(fig_weekly, full_html=False, include_plotlyjs=True,
                                            config={'responsive': True})
        else:
            chart_weekly_html = '<div class="text-center p-5"><div class="sp-loader mb-3 mx-auto"></div><p class="text-muted" style="color:var(--text-muted);">Menunggu kelengkapan data aktual (7 hari per minggu) untuk memunculkan prediksi mingguan.</p></div>'


        pred_summary = {
            'tomorrow': future_predicted[0] if future_predicted else 0,
            'next_7_days': future_week_totals[0] if future_week_totals else sum(future_predicted[:7]),
            'trend': 'increasing' if slope > 0 else 'decreasing',
            'has_2_weeks': len(parsed) >= 14
        }

    return render_template('prediction.html',
                           history=formatted_history,
                           chart_daily=chart_daily_html,
                           chart_weekly=chart_weekly_html,
                           pred_summary=pred_summary)


@app.route('/prediction/add', methods=['POST'])
@login_required
def prediction_add():
    """Simpan daily count ke MySQL parking_history."""
    try:
        date_str = request.form.get('date', '').strip()
        count    = int(request.form.get('vehicle_count', 0))
        datetime.strptime(date_str, '%Y-%m-%d')  # validasi format
        save_parking_history(date_str, count)
        flash('Data berhasil ditambahkan!', 'success')
    except Exception as e:
        flash(f'Gagal: {e}', 'danger')
    return redirect(url_for('prediction'))

@app.route('/prediction/edit/<string:date_str>', methods=['POST'])
@login_required
def prediction_edit(date_str):
    try:
        count = int(request.form.get('vehicle_count', 0))
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        ph = ParkingHistory.query.get(d)
        if ph:
            ph.vehicle_count = count
            db.session.commit()
            flash(f'Data historis untuk {date_str} berhasil diperbarui!', 'success')
        else:
            flash(f'Data untuk tanggal {date_str} tidak ditemukan.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal memperbarui: {e}', 'danger')
    return redirect(url_for('prediction'))

@app.route('/prediction/delete/<string:date_str>', methods=['POST'])
@login_required
def prediction_delete(date_str):
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        ph = ParkingHistory.query.get(d)
        if ph:
            db.session.delete(ph)
            db.session.commit()
            flash(f'Data historis untuk {date_str} berhasil dihapus!', 'success')
        else:
            flash(f'Data untuk tanggal {date_str} tidak ditemukan.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus: {e}', 'danger')
    return redirect(url_for('prediction'))


# ─── Profile ──────────────────────────────────────────────────────────────────
@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    return render_template('profile.html', user=user)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    uid  = session['user_uid']
    user = get_current_user()

    if request.method == 'POST':
        updates = {
            'nama':              request.form.get('nama', user.nama if user else ''),
            'email':             request.form.get('email', user.email if user else ''),
            'no_hp':             request.form.get('no_hp', user.no_hp if user else ''),
            'jenis_kelamin':     request.form.get('jenis_kelamin', user.jenis_kelamin if user else ''),
        }

        tanggal_lahir = request.form.get('tanggal_lahir', '').strip()
        if tanggal_lahir:
            try:
                updates['tanggal_lahir'] = datetime.strptime(tanggal_lahir, '%Y-%m-%d').date()
            except ValueError:
                pass

        save_user_profile(uid, updates)
        flash('Profil berhasil diperbarui!', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=user)


# ─── API Endpoint untuk Hardware (Tanpa Login) ────────────────────────────────
@app.route('/api/hardware/checkin', methods=['POST'])
def api_hardware_checkin():
    data = request.json
    slot_key = data.get('slot_key')
    vehicle_type = data.get('vehicle_type', 'Kecil')
    
    if not slot_key:
        return jsonify({'error': 'slot_key is required'}), 400
        
    slot_obj = ParkingSlot.query.get(slot_key)
    if not slot_obj:
        slot_obj = ParkingSlot(id=slot_key, status='Terisi', check_in=datetime.now(), vehicle_type=vehicle_type)
        db.session.add(slot_obj)
    else:
        slot_obj.status = 'Terisi'
        slot_obj.check_in = datetime.now()
        slot_obj.vehicle_type = vehicle_type
    
    # Transaksi baru akan dicatat nanti saat Checkout

    db.session.commit()
    return jsonify({'success': True, 'message': f'{slot_key} checked in as {vehicle_type}'})

@app.route('/api/hardware/checkout', methods=['POST'])
def api_hardware_checkout():
    data = request.json
    slot_key = data.get('slot_key')
    
    if not slot_key:
        return jsonify({'error': 'slot_key is required'}), 400
        
    slot_obj = ParkingSlot.query.get(slot_key)
    if not slot_obj or slot_obj.status.lower() != 'terisi':
        st = getattr(slot_obj, 'status', 'None')
        return jsonify({'error': f'ERR: {slot_key} {st}'}), 400
        
    vehicle_type = getattr(slot_obj, 'vehicle_type', 'Kecil')
    now = datetime.now()
    
    # Update Slot
    slot_obj.status = 'Tersedia'
    check_in_time = slot_obj.check_in
    slot_obj.check_in = None
    slot_obj.vehicle_type = None

    fee = 0
    duration_str = "0j 0m"
    hours_for_db = 0
    if check_in_time:
        diff = now - check_in_time
        total_seconds = diff.total_seconds()
        total_hours = total_seconds / 3600.0
        import math
        h_ceil = math.ceil(total_hours)
        h_ceil = max(1, h_ceil) # Minimum 1 jam
        hours_for_db = h_ceil
        
        fee = 5000 # Jam pertama
        if h_ceil > 1:
            if vehicle_type == 'Besar':
                fee += (h_ceil - 1) * 3000
            else:
                fee += (h_ceil - 1) * 2000
                
        h = int(total_hours)
        m = int((total_seconds % 3600) // 60)
        duration_str = f"{h}j {m}m"

    fee_formatted = f"{fee:,}".replace(',', '.')

    # Insert Transaction Baru di Checkout
    tx_id = f"TX-{now.strftime('%Y%m%d%H%M%S')}-{slot_key}"
    new_tx = Transaction(
        id=tx_id,
        slot_id=slot_key,
        transaction_date=now.date(),
        transaction_timestamp=int(now.timestamp()),
        duration_hours=hours_for_db,
        fee=fee,
        is_subscriber=False,
        vehicle_type=vehicle_type
    )
    db.session.add(new_tx)

    # Update History
    history_record = ParkingHistory.query.get(now.date())
    if history_record:
        history_record.vehicle_count += 1
    else:
        db.session.add(ParkingHistory(date=now.date(), vehicle_count=1))
        
    db.session.commit()
    return jsonify({'success': True, 'fee_formatted': fee_formatted, 'duration': duration_str})

@app.route('/api/hardware/calculate_fee', methods=['POST'])
def api_hardware_calculate_fee():
    data = request.json
    slot_key = data.get('slot_key')
    if not slot_key:
        return jsonify({'error': 'slot_key is required'}), 400
        
    slot_obj = ParkingSlot.query.get(slot_key)
    if not slot_obj or slot_obj.status.lower() != 'terisi':
        return jsonify({'error': 'Slot tidak valid'}), 400
        
    vehicle_type = getattr(slot_obj, 'vehicle_type', 'Kecil')
    now = datetime.now()
    check_in_time = slot_obj.check_in

    fee = 0
    duration_str = "0j 0m"
    if check_in_time:
        diff = now - check_in_time
        total_seconds = diff.total_seconds()
        total_hours = total_seconds / 3600.0
        import math
        h_ceil = math.ceil(total_hours)
        h_ceil = max(1, h_ceil)
        
        fee = 5000
        if h_ceil > 1:
            if vehicle_type == 'Besar':
                fee += (h_ceil - 1) * 3000
            else:
                fee += (h_ceil - 1) * 2000
                
        h = int(total_hours)
        m = int((total_seconds % 3600) // 60)
        duration_str = f"{h}j {m}m"

    fee_formatted = f"{fee:,}".replace(',', '.')
    return jsonify({'success': True, 'fee_formatted': fee_formatted, 'duration': duration_str})

@app.route('/api/hardware/nfc_tap', methods=['POST'])
def api_hardware_nfc_tap():
    data = request.json
    card_uid = data.get('card_uid')
    
    sub = Subscription.query.filter_by(card_uid=card_uid, status='active').first()
    if not sub:
        return jsonify({'success': False, 'message': 'Kartu tidak aktif/ditemukan'})
        
    slot_key = sub.slot_id
    if not slot_key:
        return jsonify({'success': False, 'message': 'Belum ada slot terdaftar'})
        
    slot_obj = ParkingSlot.query.get(slot_key)
    if not slot_obj:
        slot_obj = ParkingSlot(id=slot_key, status='Tersedia')
        db.session.add(slot_obj)
        
    if slot_obj.status == 'Terisi':
        # KENDARAAN KELUAR (CHECKOUT)
        # Insert Transaction untuk Subscriber (NFC)
        now = datetime.now()
        check_in_time = slot_obj.check_in
        
        # Cegah double tap terlalu cepat (kurang dari 10 detik) yang bikin error primary key
        if check_in_time and (now - check_in_time).total_seconds() < 10:
            return jsonify({'success': False, 'message': 'Tunggu sebentar...'})
            
        hours = 0
        if check_in_time:
            hours = (now - check_in_time).total_seconds() / 3600.0
            
        tx_id = f"TX-{now.strftime('%Y%m%d%H%M%S')}-{slot_key}"
        new_tx = Transaction(
            id=tx_id,
            slot_id=slot_key,
            user_identifier=sub.card_uid,
            transaction_date=now.date(),
            transaction_timestamp=int(now.timestamp()),
            duration_hours=int(hours),
            fee=0,  # Gratis untuk langganan
            is_subscriber=True,
            vehicle_type=getattr(slot_obj, 'vehicle_type', 'Kecil')
        )
        db.session.add(new_tx)
        
        slot_obj.status = 'Tersedia'
        slot_obj.check_in = None
        slot_obj.vehicle_type = None
            
        # Update History
        now_date = datetime.now().date()
        history_record = ParkingHistory.query.get(now_date)
        if history_record:
            history_record.vehicle_count += 1
        else:
            db.session.add(ParkingHistory(date=now_date, vehicle_count=1))
            
        db.session.commit()
        
        # Pisahkan nama agar tidak terlalu panjang
        nama_pendek = sub.name.split()[0] if len(sub.name) > 15 else sub.name
        return jsonify({
            'success': True, 
            'action': 'checkout', 
            'message': f'Terima kasih, {nama_pendek}', 
            'slot': slot_key
        })
        
    else:
        # KENDARAAN MASUK (CHECKIN)
        slot_obj.status = 'Terisi'
        slot_obj.check_in = datetime.now()
        slot_obj.vehicle_type = 'Kecil' # Asumsi tipe standar untuk mobil langganan
        
        # Transaksi baru akan dicatat nanti saat Checkout

        db.session.commit()
        
        # Pisahkan nama
        nama_pendek = sub.name.split()[0] if len(sub.name) > 15 else sub.name
        
        # Tambahkan estimasi akhir langganan
        expiry_str = sub.expired_at.strftime("%d-%m-%Y") if sub.expired_at else "Tdk Trbts"
        
        return jsonify({
            'success': True, 
            'action': 'checkin', 
            'message': f'Halo {nama_pendek}!', 
            'slot': f'Silakan ke {slot_key}',
            'expiry_date': expiry_str
        })


@app.route('/force-404')
def force_404():
    abort(404)


@app.route('/test_slots')
def test_slots():
    slots = ParkingSlot.query.all()
    return jsonify({s.id: s.status for s in slots})

@app.route('/api/hardware/get_simulations', methods=['GET'])
def get_simulations():
    """API ini dipanggil oleh Raspberry Pi untuk mengecek perintah simulasi dari web."""
    try:
        # Cari satu perintah simulasi yang ngantre
        result = db.session.execute(text("SELECT id, slot_id, vehicle_type FROM simulation_queue ORDER BY id ASC LIMIT 1")).fetchone()
        if result:
            sim_id, slot_id, vehicle_type = result
            # Hapus dari antrean agar tidak dieksekusi 2x
            db.session.execute(text("DELETE FROM simulation_queue WHERE id = :id"), {'id': sim_id})
            db.session.commit()
            
            return jsonify({
                "action": "OUT",
                "slot_id": slot_id,
                "vehicle_type": vehicle_type
            }), 200
    except Exception as e:
        db.session.rollback()
        
    return jsonify({}), 200

@app.route('/api/hardware/get_reserved', methods=['GET'])
def api_hardware_get_reserved():
    """API ini dipanggil Raspberry Pi untuk mengambil array slot mana saja yang direservasi oleh member aktif"""
    try:
        active_subs = Subscription.query.filter_by(status='active').all()
        reserved_slots = [sub.slot_id for sub in active_subs if sub.slot_id]
        
        # Buat array string "0,1,0,0,0,0"
        res_arr = []
        for i in range(1, 7):
            slot_key = f"Slot_A{i}"
            if slot_key in reserved_slots:
                res_arr.append("1")
            else:
                res_arr.append("0")
                
        reserved_str = ",".join(res_arr)
        return jsonify({"success": True, "reserved": reserved_str}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/hardware/update_stat', methods=['POST'])
def api_hardware_update_stat():
    """API ini dipanggil oleh Raspberry Pi untuk mengupdate status berdasarkan sensor Master."""
    data = request.json
    stat_str = data.get('stat_str', '')
    
    if not stat_str:
        return jsonify({'success': False, 'message': 'No stat_str provided'}), 400
        
    # stat_str format: "0,K,B,0,M,0"
    statuses = stat_str.split(',')
    
    for i, s in enumerate(statuses):
        s = s.strip()
        slot_num = i + 1
        if slot_num > 6:
            break
            
        slot_key = f'Slot_A{slot_num}'
        slot_obj = ParkingSlot.query.get(slot_key)
        
        if not slot_obj:
            slot_obj = ParkingSlot(id=slot_key, status='Tersedia')
            db.session.add(slot_obj)
            
        # Logika Update Status
        if s == '0':
            # Jika sensor Master mendeteksi kosong, tapi di DB Terisi,
            # mungkin mobil keluar tanpa bayar atau admin force open.
            # Kita amankan saja statusnya kembali ke Tersedia.
            if slot_obj.status != 'Tersedia':
                slot_obj.status = 'Tersedia'
                
        elif s == 'K' or s == 'B':
            # Jika Master mendeteksi ada mobil Kecil/Besar
            if slot_obj.status != 'Terisi':
                slot_obj.status = 'Terisi'
                slot_obj.check_in = datetime.now()
                slot_obj.vehicle_type = 'Kecil' if s == 'K' else 'Besar'
                
        elif s == 'M':
            # Member, biarkan nfc_tap yang mengurus check_in/check_out.
            # Tapi setidaknya kita pastikan statusnya Terisi secara fisik.
            if slot_obj.status != 'Terisi':
                slot_obj.status = 'Terisi'

    db.session.commit()
    return jsonify({"success": True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
