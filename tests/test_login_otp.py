import os

import pytest

if os.getenv("CI"):
    pytest.skip("Skip OTP test in CI", allow_module_level=True)

from utils.otp_helper import get_latest_otp_code


def test_get_otp():
    email_user = os.getenv("OTP_EMAIL")
    app_password = os.getenv("OTP_APP_PASSWORD")

    if not email_user or not app_password:
        pytest.skip("OTP_EMAIL/OTP_APP_PASSWORD are not set")

    code = get_latest_otp_code(
        email_user=email_user,
        app_password=app_password,
        subject_filter="код",
    )

    print("OTP CODE:", code)
