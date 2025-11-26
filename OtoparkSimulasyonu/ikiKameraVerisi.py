import cv2
import easyocr
import sqlite3
from datetime import datetime

reader = easyocr.Reader(['en'], gpu=False)

# Giriş ve çıkış kameralarının URL'leri
camera_giris_url = "http://192.168.1.45:8080/video"  # giriş telefonu
camera_cikis_url = "http://192.168.1.46:8080/video"   # çıkış telefonu

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


def vehicle_in(plate):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO vehicles (plate, status) VALUES (?, 'IN')", (plate,))
    conn.commit()
    conn.close()
    print(f"Giriş yapıldı: {plate}")

def vehicle_out(plate):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO vehicles (plate, status) VALUES (?, 'OUT')", (plate,))
    conn.commit()
    conn.close()
    print(f"Çıkış yapıldı: {plate}")

def current_count():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vehicles WHERE status='IN'")
    ins = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vehicles WHERE status='OUT'")
    outs = cur.fetchone()[0]
    conn.close()
    return ins - outs

# Maksimum otopark kapasitesi
TOPLAM_YER = 10


def read_plate(frame):
    results = reader.readtext(frame)
    for (bbox, text, prob) in results:
        text = text.upper().replace(" ", "")
        if len(text) >= 5:  # çok kısa yazıları atla
            return text
    return None


while True:
    # --- Giriş Kamerası ---
    ret_giris, frame_giris = cap_giris.read()
    if ret_giris:
        plate = read_plate(frame_giris)
        if plate:
            if current_count() < TOPLAM_YER:
                vehicle_in(plate)
            else:
                print(f"Otopark dolu! {plate} giremez.")
        cv2.putText(frame_giris, f"Boş Yer: {TOPLAM_YER - current_count()}/{TOPLAM_YER}",
                    (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        cv2.imshow("Giriş Kamera", frame_giris)

    # --- Çıkış Kamerası ---
    ret_cikis, frame_cikis = cap_cikis.read()
    if ret_cikis:
        plate = read_plate(frame_cikis)
        if plate:
            # Veritabanında varsa çıkış yap
            vehicle_out(plate)
        cv2.putText(frame_cikis, f"Boş Yer: {TOPLAM_YER - current_count()}/{TOPLAM_YER}",
                    (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        cv2.imshow("Çıkış Kamera", frame_cikis)

    # 'q' ile çıkış
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap_giris.release()
cap_cikis.release()
cv2.destroyAllWindows()

