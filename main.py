import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parent / "data" / "students.json"
SUBJECTS = (
    "Matematika",
    "Ona tili",
    "Ingliz tili",
    "Fizika",
    "Tarix",
    "Informatika",
)
QUIZZES = {
    "Matematika": (
        ("12 + 8 nechaga teng?", ("18", "20", "22"), 1),
        ("7 × 6 nechaga teng?", ("42", "36", "48"), 0),
        ("81 ning kvadrat ildizi nechaga teng?", ("8", "9", "10"), 1),
    ),
    "Ona tili": (
        ("Ot so‘z turkumi nimani bildiradi?", ("Harakatni", "Belgini", "Shaxs yoki narsani"), 2),
        ("‘Kitoblar’ so‘zidagi -lar qo‘shimchasi nimani bildiradi?", ("Ko‘plikni", "Egalikni", "Kelishikni"), 0),
        ("Qaysi biri sifat?", ("Yugurdi", "Chiroyli", "Daftar"), 1),
    ),
    "Ingliz tili": (
        ("I ___ a student.", ("am", "is", "are"), 0),
        ("‘Book’ so‘zining ko‘plik shakli qaysi?", ("Bookes", "Books", "Bookies"), 1),
        ("‘Hot’ so‘zining qarama-qarshi ma’nosi qaysi?", ("Warm", "Cold", "Big"), 1),
    ),
    "Fizika": (
        ("Kuchning o‘lchov birligi qaysi?", ("Nyuton", "Joul", "Vatt"), 0),
        ("Suv odatda necha °C da muzlaydi?", ("0 °C", "10 °C", "100 °C"), 0),
        ("Elektr toki kuchi qaysi birlikda o‘lchanadi?", ("Volt", "Amper", "Om"), 1),
    ),
    "Tarix": (
        ("Qadimgi Misr qaysi daryo bo‘yida rivojlangan?", ("Nil", "Amudaryo", "Volga"), 0),
        ("Ikkinchi jahon urushi qaysi yilda tugagan?", ("1939-yilda", "1945-yilda", "1950-yilda"), 1),
        ("Buyuk Ipak yo‘li asosan nimani bog‘lagan?", ("Sharq va G‘arbni", "Amerikalarni", "Faqat orollarni"), 0),
    ),
    "Informatika": (
        ("Ikkilik sanoq sistemasida qaysi raqamlar ishlatiladi?", ("0 va 1", "1 va 2", "0 dan 9 gacha"), 0),
        ("Kompyuterning asosiy hisoblash qurilmasi qaysi?", ("Protsessor", "Monitor", "Klaviatura"), 0),
        ("Klaviatura qanday qurilma?", ("Chiqarish", "Kiritish", "Saqlash"), 1),
    ),
}


def load_students():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_students(students):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = DATA_FILE.with_suffix(".tmp")
    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(students, file, ensure_ascii=False, indent=2)
    os.replace(temporary_file, DATA_FILE)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 300_000
    ).hex()


def take_test(student):
    print("\nTest topshiriladigan fan:")
    for number, subject in enumerate(student["subjects"], start=1):
        print(f"{number}. {subject}")

    while True:
        try:
            choice = int(input("Fan raqamini tanlang: "))
        except ValueError:
            print("Raqam kiriting.")
            continue
        if 1 <= choice <= len(student["subjects"]):
            break
        print("Ro‘yxatdagi fan raqamini tanlang.")

    subject = student["subjects"][choice - 1]
    score = 0
    questions = QUIZZES[subject]
    print(f"\n--- {subject} fanidan test ---")

    for number, (question, options, correct_answer) in enumerate(questions, start=1):
        print(f"\n{number}. {question}")
        for option_number, option in enumerate(options, start=1):
            print(f"   {option_number}. {option}")

        while True:
            try:
                answer = int(input("Javob raqami: "))
            except ValueError:
                print("Raqam kiriting.")
                continue
            if 1 <= answer <= len(options):
                break
            print("Variantlardan birini tanlang.")

        if answer - 1 == correct_answer:
            score += 1

    percentage = round(score / len(questions) * 100)
    print(f"\nO‘quvchi login: {student['username']}")
    print(f"Natija: {score}/{len(questions)} ({percentage}%).")


def choose_subjects():
    print("\nFanlar:")
    for number, subject in enumerate(SUBJECTS, start=1):
        print(f"{number}. {subject}")

    while True:
        answer = input("3 ta fan raqamini vergul bilan kiriting (masalan, 1,3,5): ")
        try:
            choices = [int(value.strip()) for value in answer.split(",")]
        except ValueError:
            print("Faqat fan raqamlarini kiriting.")
            continue

        if len(choices) != 3 or len(set(choices)) != 3:
            print("Aynan 3 ta har xil fan tanlang.")
            continue
        if any(choice < 1 or choice > len(SUBJECTS) for choice in choices):
            print("Raqamlar ro‘yxatdagi fanlardan bo‘lishi kerak.")
            continue

        return [SUBJECTS[choice - 1] for choice in choices]


def register():
    students = load_students()
    print("\n--- O‘quvchi ro‘yxatdan o‘tishi ---")
    name = input("Ism: ").strip()
    surname = input("Familiya: ").strip()
    username = input("Login yarating: ").strip()

    if not name or not surname:
        print("Ism va familiyani bo‘sh qoldirmang.")
        return
    if len(username) < 3:
        print("Login kamida 3 ta belgidan iborat bo‘lsin.")
        return
    if any(student["username"].casefold() == username.casefold() for student in students):
        print("Bu login band. Boshqa login tanlang.")
        return

    while True:
        password = input("Parol yarating (kamida 8 ta belgi): ")
        if len(password) < 8:
            print("Parol kamida 8 ta belgidan iborat bo‘lishi kerak.")
            continue
        confirmation = input("Parolni qayta kiriting: ")
        if password != confirmation:
            print("Parollar mos kelmadi. Qaytadan urinib ko‘ring.")
            continue
        break

    subjects = choose_subjects()
    salt = secrets.token_hex(16)
    students.append(
        {
            "name": name,
            "surname": surname,
            "username": username,
            "salt": salt,
            "password_hash": hash_password(password, salt),
            "subjects": subjects,
        }
    )
    save_students(students)
    print("\nRo‘yxatdan muvaffaqiyatli o‘tdingiz. Endi login qilishingiz mumkin.")


def login():
    students = load_students()
    print("\n--- O‘quvchi login qilishi ---")
    username = input("Login: ").strip()
    password = input("Parol: ")

    student = next(
        (item for item in students if item["username"].casefold() == username.casefold()),
        None,
    )
    if student is None or not hmac.compare_digest(
        hash_password(password, student["salt"]), student["password_hash"]
    ):
        print("Login yoki parol noto‘g‘ri.")
        return

    print(f"\nXush kelibsiz, {student['name']} {student['surname']}!")
    print("Tanlagan fanlaringiz: " + ", ".join(student["subjects"]))
    take_test(student)


def main():
    while True:
        print("\n=== O‘quvchilar tizimi ===")
        print("1. Ro‘yxatdan o‘tish")
        print("2. Login qilish")
        print("0. Chiqish")
        choice = input("Tanlang: ").strip()

        if choice == "1":
            register()
        elif choice == "2":
            login()
        elif choice == "0":
            print("Dastur tugadi.")
            break
        else:
            print("Noto‘g‘ri tanlov. 1, 2 yoki 0 ni kiriting.")


if __name__ == "__main__":
    main()