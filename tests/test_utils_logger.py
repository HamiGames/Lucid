# Path: tests/test_utils_logger.py
from api.app.utils import logger


def test_logger_outputs_json(capsys):
    log = logger.get_logger("test")
    log.info("hello", extra={"foo": "bar"})
    out, _ = capsys.readouterr()
    assert "hello" in out
    assert '"foo": "bar"' in out
