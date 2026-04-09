from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://front.test.kp.ktsf.ru/"
STATE_PATH = Path(__file__).resolve().parent / "state.json"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL)

        input(
            "В браузере: нажмите «Войти», введите email и код, полностью авторизуйтесь.\n"
            "Когда закончите, нажмите Enter здесь, в консоли..."
        )

        context.storage_state(path=str(STATE_PATH))
        browser.close()

    print(f"Сохранено: {STATE_PATH}")


if __name__ == "__main__":
    main()
