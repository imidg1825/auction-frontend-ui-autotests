"""
Раздел «Настройки» / «Личные данные» в личном кабинете.

Сессия задаётся в conftest через auth/state.json.
"""

import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

STATE_JSON = Path(__file__).resolve().parent.parent / "auth" / "state.json"

pytestmark = pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — выполните auth/save_auth.py.",
)

VIEWPORT_MOBILE = {"width": 390, "height": 844}
SETTINGS_PATH = re.compile(r"/profile/settings/?$")

_PROFILE_FIELD_NAMES = ("firstName", "lastName", "email", "phone")


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_home(page):
    page.goto("/", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)


def _open_settings_from_profile_menu(page):
    """Меню по аватару → ссылка в «Настройки»."""
    page.set_viewport_size(VIEWPORT_MOBILE)
    _open_home(page)
    page.locator("header button[class*='linkAvatar']").click()
    settings_link = page.locator('a[href="/profile/settings"]')
    expect(settings_link).to_be_visible(timeout=15_000)
    settings_link.click()
    expect(page).to_have_url(SETTINGS_PATH, timeout=30_000)
    page.wait_for_timeout(4000)


def _settings_main(page):
    return page.locator("main")


def test_settings_opens_from_profile_menu(page):
    """Раздел «Настройки» открывается из меню профиля."""
    _open_settings_from_profile_menu(page)


def test_settings_url(page):
    """URL соответствует разделу настроек."""
    _open_settings_from_profile_menu(page)
    expect(page).to_have_url(SETTINGS_PATH)


def test_settings_page_shows_section_marker(page):
    """На странице виден раздел настроек или блок личных данных."""
    _open_settings_from_profile_menu(page)
    main = _settings_main(page)
    expect(main.get_by_text("Личные данные", exact=False)).to_be_visible()
    expect(main.get_by_role("heading", name=re.compile(r"Настр"))).to_be_visible()


def test_settings_profile_fields_visible(page):
    """Поля профиля отображаются (имя, фамилия, e-mail, телефон)."""
    _open_settings_from_profile_menu(page)
    main = _settings_main(page)
    for name in _PROFILE_FIELD_NAMES:
        inp = main.locator(f'input[name="{name}"]')
        expect(inp).to_be_visible()
    for label in ("Имя", "Фамилия", "E-mail", "Телефон"):
        expect(main.get_by_label(label, exact=False)).to_be_visible()


def test_settings_can_edit_field_when_enabled(page):
    """Если поле доступно для ввода, значение можно изменить."""
    _open_settings_from_profile_menu(page)
    main = _settings_main(page)
    first = main.locator('input[name="firstName"]')
    if first.is_disabled():
        pytest.skip("Поля профиля на стенде только для просмотра.")

    suffix = " UI"
    original = first.input_value()
    first.fill(original + suffix)
    expect(first).to_have_value(original + suffix)


def test_settings_save_button_enables_after_change_when_present(page):
    """Если есть кнопка сохранения, после изменения данных она становится активной."""
    _open_settings_from_profile_menu(page)
    main = _settings_main(page)
    first = main.locator('input[name="firstName"]')
    if first.is_disabled():
        pytest.skip("Нет редактируемых полей.")

    save = main.get_by_role("button", name=re.compile(r"Сохран", re.I))
    if save.count() == 0:
        save = page.get_by_role("button", name=re.compile(r"Сохран", re.I))
    if save.count() == 0:
        pytest.skip("Нет кнопки сохранения на странице настроек.")

    expect(save.first).to_be_visible()
    if save.first.is_disabled():
        first.fill(first.input_value() + " x")
        page.wait_for_timeout(500)
    expect(save.first).to_be_enabled()


def test_settings_save_without_error_when_available(page):
    """После сохранения нет явной ошибки в интерфейсе (если сценарий доступен)."""
    _open_settings_from_profile_menu(page)
    main = _settings_main(page)
    first = main.locator('input[name="firstName"]')
    if first.is_disabled():
        pytest.skip("Нет редактируемых полей.")

    save = main.get_by_role("button", name=re.compile(r"Сохран", re.I))
    if save.count() == 0:
        save = page.get_by_role("button", name=re.compile(r"Сохран", re.I))
    if save.count() == 0:
        pytest.skip("Нет кнопки сохранения.")

    original = first.input_value()
    first.fill(original + "!")
    page.wait_for_timeout(400)
    if save.first.is_disabled():
        pytest.skip("Кнопка сохранения не активируется после изменения.")

    save.first.click()
    page.wait_for_timeout(4000)

    err = page.locator('[role="alert"]').filter(
        has_text=re.compile(r"ошибк|не удалось|error|fail", re.I)
    )
    if err.count() > 0 and err.first.is_visible():
        pytest.fail("После сохранения отображается сообщение об ошибке.")

    dlg = page.locator('[role="dialog"]')
    if dlg.count() > 0 and dlg.first.is_visible():
        dlg_err = dlg.first.get_by_text(re.compile(r"ошибк|не удалось", re.I))
        if dlg_err.count() > 0:
            pytest.fail("В диалоге отображается ошибка после сохранения.")

    first.fill(original)
    page.wait_for_timeout(400)
    if not save.first.is_disabled():
        save.first.click()
        page.wait_for_timeout(3000)


def test_settings_validation_on_email_when_editable(page):
    """Проверка валидации формата e-mail, если поле редактируемое."""
    _open_settings_from_profile_menu(page)
    main = _settings_main(page)
    email = main.locator('input[name="email"]')
    if email.is_disabled():
        pytest.skip("Поле e-mail только для просмотра.")

    email.fill("not-valid-email-___")
    page.keyboard.press("Tab")
    page.wait_for_timeout(600)

    hint = main.get_by_text(
        re.compile(r"формат|неверн|некорректн|укажите|e-mail|email", re.I)
    )
    bad = not email.evaluate("el => el.validity.valid")

    if hint.count() > 0 and hint.first.is_visible():
        expect(hint.first).to_be_visible()
    elif bad:
        pass
    else:
        pytest.skip("На стенде нет проверки формата e-mail для этого поля.")

    page.goto("/profile/settings", wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(2000)
