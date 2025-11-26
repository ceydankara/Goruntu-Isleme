import cv2
import easyocr

# EasyOCR okuyucu (GPU yoksa CPU ile çalışacak)
reader = easyocr.Reader(['en'], gpu=False)

# Telefon kameran / IP Webcam URL'si
camera_url = "http://172.16.12.130:8080/video"  # Kendi IP ile değiştir
cap = cv2.VideoCapture(camera_url)

if not cap.isOpened():
    print("Kamera açılamadı. IP ve bağlantıyı kontrol et.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Frame gelmedi")
        continue

    # EasyOCR ile metin tespiti
    results = reader.readtext(frame)

    for (bbox, text, prob) in results:
        # Her metni yazdır (filtre yok)
        print(f"Okunan plaka: {text}, Probability: {prob:.2f}")

        # Frame üzerine yazdır (opsiyonel)
        top_left = tuple([int(val) for val in bbox[0]])
        bottom_right = tuple([int(val) for val in bbox[2]])
        cv2.rectangle(frame, top_left, bottom_right, (0,255,0), 2)
        cv2.putText(frame, text, (top_left[0], top_left[1]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

    # Kameradan gelen görüntüyü göster
    cv2.imshow("Plaka Okuma", frame)

    # 'q' tuşuna basınca çık
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
