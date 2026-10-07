from io import BytesIO

import app as platform_app


def test_master_profile_upload_search_and_contact(tmp_path, monkeypatch):
    monkeypatch.setattr(platform_app, "DATABASE", tmp_path / "platform.db")
    monkeypatch.setattr(platform_app, "ROOT", tmp_path)
    with platform_app.app.app_context():
        platform_app.initialize()

    with platform_app.app.test_client() as client:
        with client.session_transaction() as session:
            session["csrf_token"] = "test-token"

        response = client.post(
            "/usta",
            data={
                "name": "Ali Usta",
                "phone": "+998901112233",
                "location": "Toshkent",
                "works": "Santexnika va quvur ta'miri",
                "result": "10 yillik tajriba, kafolatli ta'mir",
                "notes": "Dam olish kunlari ham ishlaydi",
                "photo": (BytesIO(b"test image"), "usta.jpg"),
                "csrf_token": "test-token",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 302
        assert list((tmp_path / "static" / "uploads").glob("master-*.jpg"))

        page = client.get("/usta?q=santexnika&location=Toshkent")
        assert page.status_code == 200
        assert b"Ali Usta" in page.data
        assert b"tel:+998901112233" in page.data
        assert b"10 yillik tajriba" in page.data

        no_match = client.get("/usta?q=elektrik")
        assert b"Ali Usta" not in no_match.data