from app.auth.email_validation import clean_account_email
from app.common.exceptions import AppError


def test_clean_account_email_strips_spaces_and_display_name() -> None:
    assert clean_account_email("  Jane  < jane.doe @ company.com > ") == "jane.doe@company.com"
    assert clean_account_email("mailto:jane.doe@company.com") == "jane.doe@company.com"


def test_clean_account_email_rejects_name_only() -> None:
    try:
        clean_account_email("Jane Employee")
    except AppError as exc:
        assert exc.code == "INVALID_EMAIL"
    else:
        raise AssertionError("expected AppError")
