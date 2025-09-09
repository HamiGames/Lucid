# Path: tests/test_models.py
from api.app.db.models.user import User
from api.app.db.models.session import RDPSession


def test_user_model_defaults():
    u = User(email="a@b.com")
    assert u.is_active
    assert u.email == "a@b.com"


def test_session_model_defaults():
    s = RDPSession(user_id="u1", host="127.0.0.1", port=3389)
    assert s.status == "pending"
