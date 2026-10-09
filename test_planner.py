from io import BytesIO

import app as planner_app


def setup_student_database(tmp_path):
    planner_app.DATABASE = tmp_path / "platform.db"
    with planner_app.app.app_context():
        planner_app.initialize()
        planner_app.db().execute(
            "INSERT INTO users (username, full_name, password_hash, role) VALUES (?, ?, ?, 'admin')",
            ("admin", "Test Admin", "hash"),
        )
        planner_app.db().execute(
            "INSERT INTO users (username, full_name, password_hash, role) VALUES (?, ?, ?, 'student')",
            ("student1", "Test Student", "hash"),
        )
        planner_app.db().commit()


def planner_client():
    client = planner_app.app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 2
        session["csrf_token"] = "test-token"
    return client


def test_student_planner_page_and_items(tmp_path):
    setup_student_database(tmp_path)
    client = planner_client()

    response = client.get("/planner")
    assert response.status_code == 200
    assert "Fokus taymeri".encode() in response.data

    response = client.post(
        "/planner",
        data={
            "csrf_token": "test-token",
            "action": "add_task",
            "title": "Matematika mashqi",
            "subject": "Matematika",
            "due_date": "2026-10-12",
            "priority": "high",
        },
    )
    assert response.status_code == 302

    response = client.post(
        "/planner",
        data={
            "csrf_token": "test-token",
            "action": "add_lesson",
            "lesson_subject": "Ingliz tili",
            "weekday": "0",
            "start_time": "09:30",
            "location": "101-xona",
        },
    )
    assert response.status_code == 302

    response = client.post(
        "/planner",
        data={
            "csrf_token": "test-token",
            "action": "add_exam",
            "exam_subject": "Tarix",
            "exam_date": "2026-10-20",
        },
    )
    assert response.status_code == 302

    page = client.get("/planner")
    assert b"Matematika mashqi" in page.data
    assert b"Ingliz tili" in page.data
    assert b"Tarix" in page.data


def test_completing_task_rewards_xp_only_once(tmp_path):
    setup_student_database(tmp_path)
    with planner_app.app.app_context():
        cursor = planner_app.db().execute(
            """INSERT INTO planner_tasks (user_id, title, subject, priority)
               VALUES (2, 'O‘qish', 'Tarix', 'medium')"""
        )
        task_id = cursor.lastrowid
        planner_app.db().commit()

    client = planner_client()
    for _ in range(2):
        response = client.post(
            f"/planner/task/{task_id}/complete",
            data={"csrf_token": "test-token"},
        )
        assert response.status_code == 302

    with planner_app.app.app_context():
        progress = planner_app.db().execute(
            "SELECT xp FROM student_progress WHERE user_id = 2"
        ).fetchone()
        task = planner_app.db().execute(
            "SELECT completed FROM planner_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        assert progress["xp"] == 10
        assert task["completed"] == 1


def test_planner_is_student_only_and_focus_minutes_are_validated(tmp_path):
    setup_student_database(tmp_path)

    client = planner_client()
    invalid = client.post(
        "/planner",
        data={"csrf_token": "test-token", "action": "focus", "minutes": "121"},
    )
    assert invalid.status_code == 302
    with planner_app.app.app_context():
        count = planner_app.db().execute(
            "SELECT COUNT(*) FROM planner_focus_sessions"
        ).fetchone()[0]
        assert count == 0

    with client.session_transaction() as session:
        session["user_id"] = 1
    assert client.get("/planner").status_code == 403


def test_postgres_query_adapts_placeholders_and_dates():
    assert planner_app.postgres_query(
        "SELECT * FROM planner_tasks WHERE date(completed_at) >= ?"
    ) == "SELECT * FROM planner_tasks WHERE CAST(completed_at AS DATE) >= %s"


def test_vercel_rejects_local_master_photo_upload(tmp_path, monkeypatch):
    setup_student_database(tmp_path)
    monkeypatch.setenv("VERCEL", "1")
    client = planner_app.app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "test-token"

    response = client.post(
        "/usta",
        data={
            "csrf_token": "test-token",
            "name": "Usta Test",
            "phone": "+998901234567",
            "location": "Toshkent",
            "works": "Ta'mirlash",
            "result": "Tajriba",
            "photo": (BytesIO(b"image data"), "usta.jpg"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Vercel fayl yuklashni saqlamaydi".encode() in response.data
    with planner_app.app.app_context():
        assert planner_app.db().execute("SELECT COUNT(*) FROM masters").fetchone()[0] == 0
