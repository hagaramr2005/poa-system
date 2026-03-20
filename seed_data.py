"""
seed_data.py — استيراد بيانات Excel إلى قاعدة البيانات
الاستخدام: python seed_data.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from app import create_app, db
from app.models import PowerOfAttorney, Client

EXCEL_PATH = os.environ.get("EXCEL_PATH", "Qanoony_Pro.xlsx")


def clean_status(raw):
    if not isinstance(raw, str):
        return "ساري"
    parts = [p.strip() for p in raw.split() if p.strip()]
    for p in reversed(parts):
        if p in ("ساري", "منتهي", "معلق"):
            return p
    return "ساري"


def run():
    app = create_app()
    with app.app_context():
        if not os.path.exists(EXCEL_PATH):
            print(f"[!] ملف Excel غير موجود: {EXCEL_PATH}")
            return

        df = pd.read_excel(EXCEL_PATH)
        df.columns = [c.strip() for c in df.columns]

        col_map = {
            "#":                      "seq",
            "رقم التوكيل بالمكتب":   "office_number",
            "موكل":                   "client_name",
            "رقم التوكيل":            "poa_number",
            "مسمى التوكيل":           "poa_title",
            "الحرف":                  "letter",
            "السنة":                  "year",
            "مكتب التوثيق":           "notary_office",
            "الحالة":                 "status_raw",
            "تاريخ انتهاء الصلاحية": "expiry_date",
            "حالة التفعيل":           "activation_status",
            # أعمدة اختيارية جديدة
            "الرقم القومي":           "national_id",
            "رقم الهاتف":             "phone",
            "العنوان":                "address",
            "المحامي":                "lawyer_name",
        }
        df.rename(columns={k: v for k, v in col_map.items() if k in df.columns},
                  inplace=True)

        imported = skipped = 0

        for _, row in df.iterrows():
            office_num = row.get("office_number")
            if pd.isna(office_num):
                skipped += 1
                continue

            office_num = int(office_num)

            if PowerOfAttorney.query.filter_by(
                    office_number=office_num, is_deleted=False).first():
                skipped += 1
                continue

            poa_number  = str(int(row["poa_number"])) \
                          if pd.notna(row.get("poa_number")) else "0"
            poa_title   = str(row.get("poa_title", "")).strip() or "توكيل عام"
            letter      = str(row.get("letter", "")).strip() \
                          if pd.notna(row.get("letter")) else None
            year        = int(row["year"]) if pd.notna(row.get("year")) else None
            notary      = str(row.get("notary_office", "")).strip() \
                          if pd.notna(row.get("notary_office")) else None
            status      = clean_status(row.get("status_raw"))
            lawyer      = str(row.get("lawyer_name", "")).strip() \
                          if pd.notna(row.get("lawyer_name")) else None

            expiry = None
            if pd.notna(row.get("expiry_date")):
                try:
                    expiry = pd.to_datetime(row["expiry_date"]).date()
                except Exception:
                    pass

            activation = str(row.get("activation_status", "مفعل")).strip()
            if activation not in ("مفعل", "غير مفعل"):
                activation = "مفعل"

            poa = PowerOfAttorney(
                office_number     = office_num,
                poa_number        = poa_number,
                poa_title         = poa_title,
                letter            = letter,
                year              = year,
                notary_office     = notary,
                status            = status,
                expiry_date       = expiry,
                activation_status = activation,
                lawyer_name       = lawyer,
            )
            db.session.add(poa)
            db.session.flush()

            # أنشئ الموكل الأساسي
            client_name = str(row.get("client_name", "")).strip() or "غير محدد"
            national_id = str(row.get("national_id", "")).strip() \
                          if pd.notna(row.get("national_id")) else None
            phone       = str(row.get("phone", "")).strip() \
                          if pd.notna(row.get("phone")) else None
            address     = str(row.get("address", "")).strip() \
                          if pd.notna(row.get("address")) else None

            db.session.add(Client(
                poa_id      = poa.id,
                is_primary  = True,
                full_name   = client_name,
                national_id = national_id,
                phone       = phone,
                address     = address,
            ))

            imported += 1

        db.session.commit()
        print(f"[✓] تم الاستيراد: {imported} | تم التخطي: {skipped}")


if __name__ == "__main__":
    run()
