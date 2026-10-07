from pathlib import Path

import app as shop_app


def setup_temp_database(tmp_path):
    shop_app.DATABASE = tmp_path / "platform.db"
    with shop_app.app.app_context():
        shop_app.initialize()
    return shop_app.DATABASE


def test_calculate_change():
    assert shop_app.calculate_change(1200, 2000) == (800, 0)
    assert shop_app.calculate_change(2000, 1500) == (0, 500)


def test_cashier_page_for_admin(tmp_path):
    setup_temp_database(tmp_path)
    with shop_app.app.app_context():
        shop_app.db().execute("DELETE FROM users")
        shop_app.db().execute(
            "INSERT INTO users (username, full_name, password_hash, role) VALUES (?, ?, ?, 'admin')",
            ("admin", "Admin User", "hash"),
        )
        shop_app.db().commit()

    with shop_app.app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 1
        response = client.get("/cashier")
        assert response.status_code == 200


def test_cashier_receipt_is_stored_and_printable(tmp_path):
    setup_temp_database(tmp_path)
    with shop_app.app.app_context():
        shop_app.db().execute("DELETE FROM users")
        shop_app.db().execute(
            "INSERT INTO users (username, full_name, password_hash, role) VALUES (?, ?, ?, 'admin')",
            ("admin", "Admin User", "hash"),
        )
        shop_app.db().commit()

    with shop_app.app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 1
            session["csrf_token"] = "test"

        client.post("/cashier", data={"action": "add_item", "product_code": "1001", "quantity": "1", "csrf_token": "test"})
        response = client.post(
            "/cashier",
            data={"action": "checkout", "payment_amount": "5000", "csrf_token": "test"},
        )

        assert response.status_code == 302
        with client.session_transaction() as session:
            assert "last_receipt" in session

        receipt_page = client.get("/receipt")
        assert receipt_page.status_code == 200
        assert b"Non" in receipt_page.data
