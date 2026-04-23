from __future__ import annotations

from pathlib import Path
from typing import Optional

import allure
import pytest
from datetime import datetime
from playwright.sync_api import Playwright


ROOT = Path(__file__).resolve().parent
AUTH_STATE_PATH = ROOT / "auth" / "state.json"
BASE_URL = "https://front.test.kp.ktsf.ru/"


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def browser_context_args(
    pytestconfig: pytest.Config,
    playwright: Playwright,
    device: Optional[str],
    base_url: Optional[str],
    _pw_artifacts_folder,
) -> dict:
    """Как в pytest-playwright, плюс storage_state из auth/state.json при наличии файла."""
    context_args: dict = {}
    if device:
        context_args.update(playwright.devices[device])
    if base_url:
        context_args["base_url"] = base_url

    if AUTH_STATE_PATH.is_file():
        context_args["storage_state"] = str(AUTH_STATE_PATH)

    video_option = pytestconfig.getoption("--video")
    if video_option in ("on", "retain-on-failure"):
        context_args["record_video_dir"] = _pw_artifacts_folder.name

    return context_args


@pytest.fixture
def guest_page(browser, base_url: str):
    """Контекст без storage_state — гостевые сценарии при наличии auth/state.json в основном контексте."""
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    yield page
    context.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        page = item.funcargs.get("page", None)

        bugs_dir = Path("bugs")
        bugs_dir.mkdir(exist_ok=True)

        safe_name = (
            item.nodeid.replace("::", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
        )
        bug_file_path = bugs_dir / f"{safe_name}.md"

        error_text = getattr(report, "longreprtext", str(report.longrepr))

        page_url = ""
        if page:
            try:
                page_url = page.url
            except Exception:
                page_url = ""

        bug_report = f"""# {item.name}

## Источник
- Тест: {item.nodeid}
- URL: {page_url or "—"}
- Время: {datetime.now().isoformat(timespec="seconds")}

## Шаги воспроизведения
1. Запустить соответствующий тест
2. Дождаться падения
3. Сверить фактическое поведение

## Ожидаемый результат
Сценарий должен выполняться без ошибки.

## Фактический результат
Тест упал.

## Сообщение об ошибке
```text
{error_text}
```
"""

        try:
            bug_file_path.write_text(bug_report, encoding="utf-8")
        except Exception as e:
            print(f"Не удалось сохранить bug report: {e}")

        allure.attach(
            bug_report,
            name="bug-report",
            attachment_type=allure.attachment_type.TEXT
        )

        if page:
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)

            test_name = item.nodeid.replace("::", "_").replace("/", "_")
            file_path = screenshots_dir / f"{test_name}.png"

            try:
                page.screenshot(path=str(file_path))
                with open(file_path, "rb") as image_file:
                    allure.attach(
                        image_file.read(),
                        name="screenshot",
                        attachment_type=allure.attachment_type.PNG
                    )
                print(f"Скриншот сохранён: {file_path}")
            except Exception as e:
                print(f"Не удалось сделать скриншот: {e}")
