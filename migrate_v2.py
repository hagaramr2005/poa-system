"""
migrate_v2.py — إضافة جداول الإشعارات والجلسات
شغّله مرة واحدة: python migrate_v2.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # db.create_all() will create new tables automatically
    db.create_all()
    print("[✓] تم إنشاء جداول notifications و user_sessions بنجاح")

    # Add avatar_filename if missing
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_filename VARCHAR(256)"))
            conn.commit()
        print("[✓] تم إضافة عمود avatar_filename")
    except Exception as e:
        if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
            print("[✓] عمود avatar_filename موجود بالفعل")
        else:
            print(f"[!] {e}")

    print("\n✅ Migration اكتملت — شغّل النظام الآن: python run.py")
