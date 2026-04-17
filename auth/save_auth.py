from pathlib import Path
import os
import sys

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.otp_helper import get_latest_otp_code

BASE_URL = "https://front.test.kp.ktsf.ru/"
STATE_PATH = Path(__file__).resolve().parent / "state.json"

EMAIL = os.getenv("OTP_EMAIL")
APP_PASSWORD = os.getenv("OTP_APP_PASSWORD")

if not EMAIL or not APP_PASSWORD:
    raise ValueError("Не заданы OTP_EMAIL или OTP_APP_PASSWORD")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL)

        page.get_by_role("button", name="Войти").click()
        page.get_by_label("E-mail").fill(EMAIL)
        page.get_by_role("button", name="Продолжить").click()

        code = get_latest_otp_code(
            email_user=EMAIL,
            app_password=APP_PASSWORD,
            subject_filter="код",
        )

        page.get_by_placeholder("Введите код").fill(code)
        page.get_by_role("button", name="Продолжить").click()

        page.wait_for_timeout(3000)
        context.storage_state(path=str(STATE_PATH))
        browser.close()

    print(f"Сохранено: {STATE_PATH}")


if __name__ == "__main__":
    main()