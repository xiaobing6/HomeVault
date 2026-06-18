from types import SimpleNamespace

from app import cli


def test_seed_cli_uses_configured_admin(monkeypatch, capsys) -> None:
    db = SimpleNamespace(closed=False)
    admin = SimpleNamespace(username="admin")
    calls = {}

    def fake_seed_auth_baseline(db_session, admin_username: str, admin_password: str):
        calls["db"] = db_session
        calls["admin_username"] = admin_username
        calls["admin_password"] = admin_password
        return admin

    def close_db() -> None:
        db.closed = True

    db.close = close_db
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(admin_username="admin", admin_password="secret"))
    monkeypatch.setattr(cli, "SessionLocal", lambda: db)
    monkeypatch.setattr(cli, "seed_auth_baseline", fake_seed_auth_baseline)

    cli.main()

    assert calls == {"db": db, "admin_username": "admin", "admin_password": "secret"}
    assert db.closed is True
    assert capsys.readouterr().out.strip() == "管理员账号已就绪: admin"
