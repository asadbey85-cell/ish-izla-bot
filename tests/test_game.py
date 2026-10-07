import app as platform_app


def test_game_page_and_assets_are_public():
    with platform_app.app.test_client() as client:
        page = client.get("/game")
        assert page.status_code == 200
        assert b"Tungi navbatchi" in page.data
        assert b"game-mount" in page.data

        script = client.get("/static/game.js")
        stylesheet = client.get("/static/game.css")
        hero_art = client.get("/static/images/night-runner.svg")
        assert script.status_code == 200
        assert b"toggleWeb" in script.data
        assert stylesheet.status_code == 200
        assert hero_art.status_code == 200