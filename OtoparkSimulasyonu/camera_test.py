import cv2

url = "http://172.16.12.130:8080/video"   # BURAYI KENDİ IP ADRESİNLE DEĞİŞTİR
cap = cv2.VideoCapture(url)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Görüntü alınamadı!")
        continue

    cv2.imshow("Telefon Kamerasi", frame)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
