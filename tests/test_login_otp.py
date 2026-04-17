import os

import pytest

if os.getenv("CI"):
    pytest.skip("Skip OTP test in CI", allow_module_level=True)

from utils.otp_helper import get_latest_otp_code

def test_get_otp():
    code = get_latest_otp_code(
        email_user="imidg18251972@gmail.com",
        app_password="muqzngmkoxhskeqh",
        subject_filter="код"
    )

    print("OTP CODE:", code)
