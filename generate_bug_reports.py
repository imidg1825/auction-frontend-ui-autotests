"""
Генерация черновиков баг-репортов из pytest JUnit XML (reports/junit.xml).
Использует только стандартную библиотеку Python.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

REPORTS_DIR = Path("reports")
JUNIT_PATH = REPORTS_DIR / "junit.xml"
BUGS_DIR = Path("bugs")
SCREENSHOTS_DIR = Path("screenshots")

# Имена, зарезервированные в Windows для устройств.
_WINDOWS_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def sanitize_filename(test_name: str, max_length: int = 180) -> str:
    """
    Убирает символы, недопустимые в имени файла Windows, и возвращает безопасное
    имя без расширения (для последующего добавления .md).
    """
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if c in invalid else c for c in test_name)
    cleaned = "".join(c for c in cleaned if ord(c) >= 32)
    cleaned = cleaned.strip().strip(".")

    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")

    if not cleaned:
        cleaned = "unnamed_test"

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip("._ ")

    if cleaned.upper() in _WINDOWS_RESERVED:
        cleaned = f"test_{cleaned}"

    return cleaned


def _full_test_name(case: ET.Element) -> str:
    classname = (case.get("classname") or "").strip()
    name = (case.get("name") or "").strip()
    if classname and name:
        return f"{classname}::{name}"
    return name or classname or "unknown_test"


def _stem_from_nodeid_like(nodeid_like: str) -> str:
    """Как в conftest: item.nodeid с заменой :: и /."""
    return nodeid_like.replace("::", "_").replace("/", "_")


def _screenshot_stem_candidates(case: ET.Element) -> list[str]:
    """Варианты stem без .png, максимально близко к nodeid Playwright/pytest."""
    name = (case.get("name") or "").strip()
    if not name:
        return []

    candidates: list[str] = []
    file_attr = (case.get("file") or "").strip()
    if file_attr:
        candidates.append(_stem_from_nodeid_like(f"{file_attr}::{name}"))

    classname = (case.get("classname") or "").strip()
    if classname:
        candidates.append(_stem_from_nodeid_like(f"{classname}::{name}"))
        if "." in classname and "/" not in classname:
            path_py = classname.replace(".", "/") + ".py"
            candidates.append(_stem_from_nodeid_like(f"{path_py}::{name}"))

    seen: set[str] = set()
    out: list[str] = []
    for s in candidates:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _find_screenshot_relpath(case: ET.Element) -> str | None:
    if not SCREENSHOTS_DIR.is_dir():
        return None
    for stem in _screenshot_stem_candidates(case):
        png = SCREENSHOTS_DIR / f"{stem}.png"
        if png.is_file():
            return f"screenshots/{png.name}"
    return None


def _failure_text(case: ET.Element) -> str:
    for tag in ("failure", "error"):
        el = case.find(tag)
        if el is not None:
            parts: list[str] = []
            msg = (el.get("message") or "").strip()
            if msg:
                parts.append(msg)
            body = (el.text or "").strip()
            if body:
                parts.append(body)
            if parts:
                return "\n\n".join(parts)
            return "(сообщение отсутствует в XML)"
    return "(элемент failure/error не найден)"


def _collect_failed_cases(root: ET.Element) -> list[ET.Element]:
    failed: list[ET.Element] = []
    for case in root.iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            failed.append(case)
    return failed


def _unique_bug_path(bugs_dir: Path, stem: str) -> Path:
    path = bugs_dir / f"{stem}.md"
    if not path.exists():
        return path
    for i in range(2, 10_000):
        candidate = bugs_dir / f"{stem}_{i}.md"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Не удалось подобрать уникальное имя для {stem}.md")


def _write_bug_report(
    path: Path,
    title: str,
    full_name: str,
    error_text: str,
    screenshot_relpath: str | None = None,
) -> None:
    screenshot_section = ""
    if screenshot_relpath:
        screenshot_section = f"## Скриншот\n`{screenshot_relpath}`\n"

    content = f"""# {title}

## Источник
- Тест: {full_name}

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
{screenshot_section}## Окружение
- Стенд: https://front.test.kp.ktsf.ru/
- Браузер: Chromium
- Источник: автогенерация из pytest junit.xml

## Примечание
Черновик создан автоматически после failed-прогона.
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    print("Генерация баг-репортов из JUnit XML…")

    if not REPORTS_DIR.is_dir():
        print(f"Папка не найдена: {REPORTS_DIR.resolve()}")
        print("Создайте каталог reports/ и положите туда junit.xml (например, pytest --junitxml=reports/junit.xml).")
        return 1

    if not JUNIT_PATH.is_file():
        print(f"Файл отчёта не найден: {JUNIT_PATH.resolve()}")
        print("Запустите pytest с опцией --junitxml=reports/junit.xml")
        return 1

    try:
        tree = ET.parse(JUNIT_PATH)
    except ET.ParseError as e:
        print(f"Не удалось разобрать XML: {e}")
        return 1

    root = tree.getroot()
    failed_cases = _collect_failed_cases(root)

    if not failed_cases:
        print("В отчёте нет упавших тестов (failed). Новые файлы в bugs/ не создаются.")
        return 0

    BUGS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Найдено упавших тестов: {len(failed_cases)}")
    print(f"Каталог для отчётов: {BUGS_DIR.resolve()}")

    for case in failed_cases:
        full_name = _full_test_name(case)
        title = full_name.split("::")[-1] if "::" in full_name else full_name
        stem = sanitize_filename(full_name)
        out_path = _unique_bug_path(BUGS_DIR, stem)
        error_text = _failure_text(case)
        shot = _find_screenshot_relpath(case)
        _write_bug_report(out_path, title, full_name, error_text, shot)
        print(f"  создан: {out_path.name}")

    print("Готово.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

def test_fail_for_debug():
    assert False, "Тестовое падение для проверки автоскрина и баг-репорта"
    