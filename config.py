import os

class Config:
    # Secret Key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-parking-secret-key-2025')

    # Upload folder for profile photos
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'uploads', 'profile')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # MySQL / MariaDB (lokal — Raspberry Pi)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:root@localhost/smart_parking'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
