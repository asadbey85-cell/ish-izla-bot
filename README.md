# Bilim maydoni

Brauzerda ishlaydigan platforma: o‘quvchi akkaunti, Ingliz tili/Matematika/Tarix testlari, avtomatik natija, reyting va admin savol qo‘shish paneli. Usta katalogida ism, telefon, shahar/tuman, rasm, xizmatlar, tajriba va natijalarni e’lon qilish mumkin; mijozlar xizmat yoki joy bo‘yicha qidirib, ustaga bevosita qo‘ng‘iroq qiladi.

O‘quvchi `/planner` sahifasida haftalik dars jadvali, muhimlik bo‘yicha saralangan uy vazifalari, imtihon sanalari, fokus taymeri, haftalik o‘qish statistikasi va XP mukofotlarini boshqaradi. Vazifa bajarilganda bir marta 10 XP beriladi; reja ma’lumotlari o‘quvchi akkauntiga bog‘langan holda SQLite bazasida saqlanadi.

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

## Vercel va Neon PostgreSQL’da hosting

Flask ilovasi Vercel Python runtime’da ishlaydi; akkauntlar, ish e’lonlari, test natijalari va o‘quvchi rejasi doimiy Neon PostgreSQL bazasida saqlanadi. Vercel loyiha fayllar tizimi vaqtinchalik bo‘lgani uchun SQLite bazasi va yuklangan rasm fayllari u yerda ishlatilmaydi. Usta rasmlari uchun tashqi HTTPS rasm havolasidan foydalaning.

1. GitHub’dagi `asadbey85-cell/ish-izla-bot` repozitoriysini Vercel’da **New Project** orqali import qiling; framework sifatida **Other** yoki avtomatik Python aniqlashni tanlang. `build.py` Vercel uchun `static/` fayllarini `public/static/` ichiga tayyorlaydi; ular CDN’dan beriladi.
2. Vercel Marketplace’dan Neon PostgreSQL’ni ulang. Neon’dan olingan PostgreSQL connection string’ni Vercel Production environment’da `DATABASE_URL` nomi bilan saqlang. `DATABASE_URL` ichida TLS (`sslmode=require`) yoqilgan bo‘lishi kerak.
3. Vercel **Environment Variables** bo‘limida `SECRET_KEY` nomli maxfiy qiymat yarating (kamida 32 tasodifiy bayt). Uni kodga yoki GitHub’ga yozmang.
4. Loyihani deploy qiling. Dastur bazadagi jadvallarni birinchi ishga tushishda yaratadi; so‘ng `https://LOYIHA-NOMI.vercel.app/jobs` ochiladi. O‘quvchi rejasi `/planner` sahifasida.

Mavjud kompyuterdagi `data/platform.db` bazasi avtomatik ko‘chmaydi; yangi Neon bazasi bo‘sh holatda boshlanadi. Eski hisoblar va e’lonlarni ko‘chirish zarur bo‘lsa, alohida xavfsiz migratsiya kerak. Neon loyiha uchun alohida development branch yaratib, production connection string’ni faqat Vercel server-side environment’da saqlang.

## Bepul onlayn joylash (PythonAnywhere)

PythonAnywhere bepul hisobida bitta web-ilova bor. Bepul rejaning CPU (kuniga 100 soniya), disk (512 MB) va tashqi internet cheklovlari mavjud; past trafikdagi sayt ishlashi mumkin, lekin tashqi CDN rasmlari yoki o‘yin yuklanmasligi mumkin. Sayt kompyuteringiz o‘chiq bo‘lsa ham `https://FOYDALANUVCHI.pythonanywhere.com/jobs` manzilida ishlaydi.

1. [PythonAnywhere Beginner hisobini](https://www.pythonanywhere.com/registration/register/beginner/) oching.
2. Loyihaning ildiz papkasida PowerShell’ga quyidagini kiriting. Arxiv `data` ichidagi SQLite bazasini ham o‘z ichiga oladi:

	```powershell
	Compress-Archive -Path app.py,wsgi.py,requirements.txt,templates,static,data -DestinationPath ish-izla.zip -Force
	```

3. PythonAnywhere’dagi **Files** sahifasidan `ish-izla.zip` arxivini yuklang. **Consoles** sahifasida Bash konsoli ochib, arxivni oching va Flask’ni o‘rnating:

	```bash
	mkdir -p ~/ish-izla
	unzip ~/ish-izla.zip -d ~/ish-izla
	mkvirtualenv --python=/usr/bin/python3.13 ish-izla
	pip install -r ~/ish-izla/requirements.txt
	```

4. **Web** sahifasida yangi web app yarating: **Manual configuration** va Python 3.13 ni tanlang. Virtualenv maydoniga `/home/FOYDALANUVCHI/.virtualenvs/ish-izla` ni kiriting.
5. Web sahifasidagi WSGI konfiguratsiya faylini ochib, Flask bo‘limini quyidagiga almashtiring. `FOYDALANUVCHI` o‘rniga PythonAnywhere foydalanuvchi nomingizni yozing:

	```python
	import sys
	project_home = "/home/FOYDALANUVCHI/ish-izla"
	if project_home not in sys.path:
		 sys.path.insert(0, project_home)
	from wsgi import application
	```

6. Web sahifasidagi **Environment variables** bo‘limida `SECRET_KEY` ni uzun, tasodifiy qiymat bilan belgilang. Bu qiymatni GitHub’ga yuklamang.
7. **Web** sahifasida **Reload** ni bosing. Sayt `https://FOYDALANUVCHI.pythonanywhere.com/jobs` manzilida ochiladi. `platform.db` loyiha ichidagi `data` papkasida saqlanadi; kodni keyin qayta yuklaganda mavjud bazani o‘chirib yubormang.
8. Birinchi marta saytni ochganda admin akkauntini yarating. O‘quvchi hisoblari `/register` sahifasida ochiladi; reja paneli `/planner` manzilida.

PythonAnywhere rejasi va cheklovlari o‘zgarishi mumkin; hisob ochishda bepul reja tafsilotlarini tekshiring. Parolingizni hech kimga yubormang.