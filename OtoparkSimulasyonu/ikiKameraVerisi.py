import cv2
import easyocr
import sqlite3
from datetime import datetime, timedelta
import time
import re


reader = easyocr.Reader(['en'], gpu=False)

camera_giris_url = "http://172.16.12.130:8080/video"
camera_cikis_url = "http://172.16.23.1:8080/video"

cap_giris = cv2.VideoCapture(camera_giris_url)
cap_cikis = cv2.VideoCapture(camera_cikis_url)

if not cap_giris.isOpened() or not cap_cikis.isOpened():
    print("Kameralardan biri açılamadı. IP ve bağlantıları kontrol et.")
    exit()


DB_FILE = "parking.db"

def db_init():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT,
            status TEXT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

db_init()


# In-memory son görüldüğü zaman (debounce)
# { plate_str : last_seen_epoch_seconds }
last_seen = {}

DEBOUNCE_SECONDS = 8

def normalize_plate_text(text: str) -> str:
    """Büyük harfe çevir, boşluk kaldır, sadece alfanümerik karakterleri al."""
    t = text.upper().replace(" ", "")
    t = re.sub(r'[^A-Z0-9]', '', t)
    return t

def get_last_status(plate):
    """Veritabanından plakanın son kaydının status'ünü getirir. Yoksa None döner."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT status FROM vehicles WHERE plate = ? ORDER BY time DESC, id DESC LIMIT 1", (plate,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def insert_status(plate, status):
    """Yeni kayıt ekle (zaman otomatik ayarlanır)."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO vehicles (plate, status) VALUES (?, ?)", (plate, status))
    conn.commit()
    conn.close()

def vehicle_in(plate):
    """Sadece son kayıt IN değilse IN ekle."""
    last = get_last_status(plate)
    if last == 'IN':
        print(f"[Atlandı] Zaten içeride: {plate}")
        return False
    insert_status(plate, 'IN')
    print(f"Giriş yapıldı: {plate}")
    return True

def vehicle_out(plate):
    """Sadece son kayıt OUT değilse ve son kayıt IN ise OUT ekle."""
    last = get_last_status(plate)
    if last is None:
        # Hatta istersen burada da OUT kaydı atma veya bir uyarı bas
        print(f"[Atlandı] Çıkış kaydı yok (daha önce giriş görünmüyor): {plate}")
        return False
    if last == 'OUT':
        print(f"[Atlandı] Zaten çıkmış: {plate}")
        return False
    # last == 'IN' ise çıkışı kaydet
    insert_status(plate, 'OUT')
    print(f"Çıkış yapıldı: {plate}")
    return True

def current_count():
    """
    Her plakanın en son kaydına bakıp şu anda içeride olan araç sayısını döndürür.
    SQL: (her plaka için max(time) al, o max zamanlı row'un status'ü IN ise say)
    """
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT v.plate
            FROM vehicles v
            JOIN (
                SELECT plate, MAX(time) AS maxtime
                FROM vehicles
                GROUP BY plate
            ) m ON v.plate = m.plate AND v.time = m.maxtime
            WHERE v.status = 'IN'
            GROUP BY v.plate
        ) sub
    """)
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def read_plate(frame):
    results = reader.readtext(frame)
    best = None
    best_prob = 0.0
    for (bbox, text, prob) in results:
        if prob < 0.3:
            continue
        text_n = normalize_plate_text(text)
        if len(text_n) >= 5 and prob > best_prob:
            best = text_n
            best_prob = prob
    return best

def should_process_plate(plate):
    """Debounce: eğer son görülen zamandan < DEBOUNCE ise atla."""
    now = time.time()
    last = last_seen.get(plate)
    if last and (now - last) < DEBOUNCE_SECONDS:
        return False
    last_seen[plate] = now
    return True


TOPLAM_YER = 10

while True:
    # --- Giriş Kamerası ---
    ret_giris, frame_giris = cap_giris.read()
    if ret_giris:
        plate = read_plate(frame_giris)
        if plate:
            if should_process_plate(plate):
                if current_count() < TOPLAM_YER:
                    vehicle_in(plate)
                else:
                    print(f"Otopark dolu! {plate} giremez.")
            else:
                # debounce nedeniyle atlandı
                pass
        cv2.putText(frame_giris, f"Boş Yer: {TOPLAM_YER - current_count()}/{TOPLAM_YER}",
                    (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        cv2.imshow("Giriş Kamera", frame_giris)

    # --- Çıkış Kamerası ---
    ret_cikis, frame_cikis = cap_cikis.read()
    if ret_cikis:
        plate = read_plate(frame_cikis)
        if plate:
            if should_process_plate(plate):
                vehicle_out(plate)
            else:
                # debounce nedeniyle atlandı
                pass
        cv2.putText(frame_cikis, f"Boş Yer: {TOPLAM_YER - current_count()}/{TOPLAM_YER}",
                    (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        cv2.imshow("Çıkış Kamera", frame_cikis)

    # 'q' tuşu ile çıkış
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap_giris.release()
cap_cikis.release()
cv2.destroyAllWindows()


