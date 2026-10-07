# Bilim maydoni

Brauzerda ishlaydigan platforma: o‘quvchi akkaunti, Ingliz tili/Matematika/Tarix testlari, avtomatik natija, reyting va admin savol qo‘shish paneli. Usta katalogida ism, telefon, shahar/tuman, rasm, xizmatlar, tajriba va natijalarni e’lon qilish mumkin; mijozlar xizmat yoki joy bo‘yicha qidirib, ustaga bevosita qo‘ng‘iroq qiladi.

Usta rasmlari JPG, PNG yoki WEBP formatida, 5 MB gacha yuklanadi va `static/uploads/` ichida saqlanadi. Yuklangan rasmlar foydalanuvchi ma’lumoti hisoblanadi va Git orqali ulashilmaydi.

## Tungi navbatchi o‘yini

`/game` sahifasida shahar tomlari orasida tebranib, 12 ta energiya belgisini yig‘ing va dronlardan qoching. Kompyuterda A/D yoki strelkalar yurish, Space sakrash, E to‘rni otish/uzish uchun; telefonda ekrandagi tugmalar ishlaydi. Phaser o‘yin dvigateli CDN’dan yuklanadi, shu sabab o‘ynash uchun internet aloqasi kerak.

## Ishga tushirish

```powershell
python -m pip install -r requirements.txt
python app.py
```

Sayt `http://127.0.0.1:5000` manzilida ochiladi. Birinchi kirishda admin akkaunti yaratiladi. O‘quvchilar `Ro‘yxatdan o‘tish` orqali akkaunt ochadi. Ma’lumotlar `data/platform.db` SQLite faylida saqlanadi.

Internetga ommaviy joylashdan oldin `SECRET_KEY` muhit o‘zgaruvchisini belgilang va HTTPS hamda ishlab chiqarish serveridan foydalaning. `main.py` avvalgi konsol dasturi sifatida qoldirilgan.