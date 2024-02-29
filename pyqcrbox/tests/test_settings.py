import pytest

from pyqcrbox import settings


@pytest.mark.no_adjust_settings
def test_default_database_settings():
    """
    THe default database should be an in-memory SQLite database.
    """
    assert settings.db.url == "sqlite:///:memory:"
