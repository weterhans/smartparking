"""
auth_routes.py
Autentikasi lokal (MySQL + bcrypt) — register & forgot password.
"""

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from local_auth import (
    create_local_user,
    save_user_profile,
    get_user_profile,
)

auth_bp = Blueprint('auth', __name__)


# ==================== REGISTER ====================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_uid'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        nama     = request.form.get('nama', '').strip()
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        no_hp    = request.form.get('no_hp', '').strip()

        if not nama or not username or not email or not password or not no_hp:
            flash('Semua field wajib diisi.', 'danger')
            return render_template('register.html')

        try:
            uid = create_local_user(
                email=email,
                password=password,
                username=username,
                nama=nama,
                no_hp=no_hp,
            )
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            msg = str(e)
            if 'EMAIL_EXISTS' in msg:
                flash('Email sudah terdaftar. Gunakan email lain.', 'danger')
            elif 'USERNAME_EXISTS' in msg:
                flash('Username sudah dipakai. Gunakan username lain.', 'danger')
            else:
                flash(f'Registrasi gagal: {msg}', 'danger')

    return render_template('register.html')


# ==================== FORGOT PASSWORD ====================
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """
    Fitur reset password dinonaktifkan di mode lokal.
    Halaman tetap ditampilkan dengan pesan informatif.
    """
    if request.method == 'POST':
        flash('Fitur reset password tidak tersedia dalam mode lokal. '
              'Hubungi administrator untuk mereset password Anda.', 'warning')
    return render_template('forgot_password.html')
