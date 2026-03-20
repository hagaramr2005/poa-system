"""
backup.py — نسخ احتياطي تلقائي لقاعدة البيانات
الاستخدام: python backup.py
يمكن جدولته كـ Task Scheduler على Windows أو Cron على Linux
"""
import os, shutil
from datetime import datetime

DB_PATH     = os.path.join(os.path.dirname(__file__), "instance", "qanoony.db")
BACKUP_DIR  = os.path.join(os.path.dirname(__file__), "backups")
KEEP_LATEST = 30   # احتفظ بآخر 30 نسخة فقط

def run():
    if not os.path.exists(DB_PATH):
        print("[!] قاعدة البيانات غير موجودة")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"qanoony_{timestamp}.db"
    dest        = os.path.join(BACKUP_DIR, backup_name)

    shutil.copy2(DB_PATH, dest)
    size = os.path.getsize(dest) / 1024
    print(f"[✓] تم النسخ الاحتياطي: {backup_name} ({size:.1f} KB)")

    # حذف النسخ القديمة
    backups = sorted([
        f for f in os.listdir(BACKUP_DIR) if f.startswith("qanoony_") and f.endswith(".db")
    ])
    if len(backups) > KEEP_LATEST:
        to_delete = backups[:len(backups) - KEEP_LATEST]
        for f in to_delete:
            os.remove(os.path.join(BACKUP_DIR, f))
        print(f"[✓] حُذفت {len(to_delete)} نسخة قديمة")

if __name__ == "__main__":
    run()
