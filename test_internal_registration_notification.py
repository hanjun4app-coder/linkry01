import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


def test_internal_registration_email_content_excludes_sensitive_data(monkeypatch):
    from app import email_service

    captured = {}

    def fake_send_mailgun_email(to_email, subject, text_body, html_body):
        captured["to_email"] = to_email
        captured["subject"] = subject
        captured["text_body"] = text_body
        captured["html_body"] = html_body
        return {"sent": True, "provider": "mailgun"}

    monkeypatch.setattr(email_service.settings, "INTERNAL_NOTIFICATION_EMAIL", "hanjun4app@gmail.com")
    monkeypatch.setattr(email_service.settings, "MAILGUN_API_KEY", "test_mailgun_key")
    monkeypatch.setattr(email_service.settings, "MAILGUN_DOMAIN", "mg.safehome.test")
    monkeypatch.setattr(email_service.settings, "MAILGUN_FROM", "SafeHome <support@safehome.test>")
    monkeypatch.setattr(email_service, "_send_mailgun_email", fake_send_mailgun_email)

    result = email_service.send_internal_registration_completed_email(
        customer_email="customer@example.com",
        user_id="123",
        family_id="family_123",
    )

    assert result["sent"] is True
    assert captured["to_email"] == "hanjun4app@gmail.com"
    assert captured["subject"] == "New SafeHome registration completed"
    assert "Customer email: customer@example.com" in captured["text_body"]
    assert "User ID: 123" in captured["text_body"]
    assert "Family ID: family_123" in captured["text_body"]
    assert "Registration completion time:" in captured["text_body"]
    assert "Source: SafeHome onboarding" in captured["text_body"]

    combined_body = captured["text_body"] + captured["html_body"]
    assert "password" not in combined_body.lower()
    assert "setup token" not in combined_body.lower()
    assert "jwt" not in combined_body.lower()
    assert "test_mailgun_key" not in combined_body


def test_missing_internal_notification_email_is_non_blocking(monkeypatch, caplog):
    from app import email_service

    monkeypatch.setattr(email_service.settings, "INTERNAL_NOTIFICATION_EMAIL", "")

    result = email_service.send_internal_registration_completed_email(
        customer_email="customer@example.com",
        user_id="123",
        family_id="family_123",
    )

    assert result["sent"] is False
    assert result["skipped"] is True
    assert result["reason"] == "missing_internal_notification_email"
    assert "INTERNAL_NOTIFICATION_EMAIL is not configured" in caplog.text


def test_mailgun_failure_is_non_blocking(monkeypatch):
    from app import email_service

    def fake_send_mailgun_email(to_email, subject, text_body, html_body):
        return {"sent": False, "provider": "mailgun"}

    monkeypatch.setattr(email_service.settings, "INTERNAL_NOTIFICATION_EMAIL", "hanjun4app@gmail.com")
    monkeypatch.setattr(email_service.settings, "MAILGUN_API_KEY", "test_mailgun_key")
    monkeypatch.setattr(email_service.settings, "MAILGUN_DOMAIN", "mg.safehome.test")
    monkeypatch.setattr(email_service.settings, "MAILGUN_FROM", "SafeHome <support@safehome.test>")
    monkeypatch.setattr(email_service, "_send_mailgun_email", fake_send_mailgun_email)

    result = email_service.send_internal_registration_completed_email(
        customer_email="customer@example.com",
        user_id="123",
        family_id="family_123",
    )

    assert result["sent"] is False
    assert result["provider"] == "mailgun"


def test_setup_password_sends_internal_notification_after_success(monkeypatch):
    from app.routes import auth

    sent = {}
    fake_user = SimpleNamespace(
        id=123,
        email="customer@example.com",
        role="family",
        family_id=456,
        hashed_password="",
        updated_at=None,
    )
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = fake_user

    monkeypatch.setattr(auth, "enforce_rate_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(auth, "verify_password_setup_token", lambda token: {"sub": "123"})
    monkeypatch.setattr(auth, "get_password_hash", lambda password: "hashed-password")

    def fake_notify(customer_email, user_id="", family_id=""):
        sent["customer_email"] = customer_email
        sent["user_id"] = user_id
        sent["family_id"] = family_id
        return {"sent": True}

    monkeypatch.setattr(auth, "send_internal_registration_completed_email", fake_notify)

    response = asyncio.run(auth.setup_password(
        auth.SetupPasswordRequest(
            token="valid-token",
            password="Password1",
            password_confirm="Password1",
        ),
        db=fake_db,
    ))

    assert response["success"] is True
    assert fake_user.hashed_password == "hashed-password"
    fake_db.commit.assert_called_once()
    assert sent == {
        "customer_email": "customer@example.com",
        "user_id": "123",
        "family_id": "456",
    }


def test_setup_password_validation_failure_does_not_send_notification(monkeypatch):
    from app.routes import auth

    fake_db = MagicMock()
    notify = MagicMock()
    monkeypatch.setattr(auth, "enforce_rate_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(auth, "send_internal_registration_completed_email", notify)

    with pytest.raises(HTTPException):
        asyncio.run(auth.setup_password(
            auth.SetupPasswordRequest(
                token="valid-token",
                password="Password1",
                password_confirm="Password2",
            ),
            db=fake_db,
        ))

    notify.assert_not_called()
    fake_db.commit.assert_not_called()
