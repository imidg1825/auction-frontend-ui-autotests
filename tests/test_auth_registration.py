import re
import uuid

import pytest
from playwright.sync_api import expect


BASE_URL = "https://front.test.kp.ktsf.ru/"


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_login_modal(page):
    page.goto(BASE_URL, wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)
    page.get_by_role("button", name="Войти").click()


def _auth_dialog(page):
    dlg = page.locator('[role="dialog"]').first
    expect(dlg).to_be_visible()
    return dlg


def test_sign_in_opens_modal_with_login_and_registration(guest_page):
    """По «Войти» открывается поп-ап входа с переходом к регистрации."""
    _open_login_modal(guest_page)
    dlg = _auth_dialog(guest_page)
    expect(dlg.get_by_text("Вход", exact=True)).to_be_visible()
    expect(dlg.get_by_text("Зарегистрироваться", exact=False)).to_be_visible()


def test_login_email_field_accepts_value(guest_page):
    """Поле e-mail на шаге входа принимает введённое значение."""
    _open_login_modal(guest_page)
    dlg = _auth_dialog(guest_page)
    email = dlg.locator('input[type="email"]')
    value = "uitest@example.com"
    email.fill(value)
    expect(email).to_have_value(value)


def test_login_continue_button_enables_for_valid_email_only(guest_page):
    """Некорректный e-mail оставляет «Продолжить» неактивной; корректный — активирует."""
    _open_login_modal(guest_page)
    dlg = _auth_dialog(guest_page)
    email = dlg.locator('input[type="email"]')
    btn = dlg.get_by_role("button", name="Продолжить")

    expect(btn).to_be_disabled()
    email.fill("not-an-email")
    expect(btn).to_be_disabled()

    email.fill("user@example.com")
    expect(btn).to_be_enabled()


def test_login_continue_opens_code_verification_screen(guest_page):
    """После «Продолжить» показывается экран ввода одноразового кода."""
    _open_login_modal(guest_page)
    dlg = _auth_dialog(guest_page)
    dlg.locator('input[type="email"]').fill(f"uitest.{uuid.uuid4().hex[:12]}@example.com")
    dlg.get_by_role("button", name="Продолжить").click()

    expect(dlg.get_by_text("одноразовый код", exact=False)).to_be_visible(timeout=30_000)
    expect(dlg.get_by_placeholder("Введите код")).to_be_visible()


def test_code_field_accepts_digit_input(guest_page):
    """Поле кода принимает ввод цифр (без проверки корректности кода)."""
    _open_login_modal(guest_page)
    dlg = _auth_dialog(guest_page)
    dlg.locator('input[type="email"]').fill(f"uitest.{uuid.uuid4().hex[:12]}@example.com")
    dlg.get_by_role("button", name="Продолжить").click()
    code_input = dlg.get_by_placeholder("Введите код")
    expect(code_input).to_be_visible(timeout=30_000)

    code_input.fill("12345")
    expect(code_input).to_have_value("12345")


@pytest.mark.skip(reason="Нужен реальный код из письма; экран «Персональные данные» после него здесь не проверяем.")
def test_after_valid_code_personal_data_screen_opens(guest_page):
    """После верного кода должен открыться экран персональных данных (требует OTP)."""
    pass


def _open_registration_personal_data_form(page):
    _open_login_modal(page)
    dlg = _auth_dialog(page)
    dlg.get_by_text("Зарегистрироваться", exact=False).click()
    expect(dlg.get_by_text("Регистрация", exact=True)).to_be_visible()
    expect(dlg.get_by_text("персональные данные", exact=False)).to_be_visible()
    return dlg


def test_registration_name_and_phone_fields_are_editable(guest_page):
    """На форме регистрации доступны поля имени и телефона."""
    dlg = _open_registration_personal_data_form(guest_page)
    name = dlg.get_by_label("Имя", exact=False)
    phone = dlg.get_by_label("Номер телефона", exact=False)

    name.fill("Анна")
    phone.fill("+79001234567")
    expect(name).to_have_value("Анна")
    expect(phone).to_have_value(re.compile(r"\+7 \(900\) 123 45 67"))


def test_registration_consent_can_be_checked(guest_page):
    """Чекбокс согласия с условиями можно установить."""
    dlg = _open_registration_personal_data_form(guest_page)
    dlg.get_by_text("Я соглашаюсь", exact=False).click()
    expect(dlg.locator('input[type="checkbox"]')).to_be_checked()


def test_registration_save_button_enabled_when_form_valid(guest_page):
    """При заполненных данных и согласии кнопка «Сохранить» активна."""
    dlg = _open_registration_personal_data_form(guest_page)
    dlg.get_by_label("Имя", exact=False).fill("Иван")
    dlg.locator('input[type="email"]').fill("ivan.reg@example.com")
    dlg.get_by_label("Номер телефона", exact=False).fill("+79001112233")
    dlg.get_by_text("Я соглашаюсь", exact=False).click()

    save = dlg.get_by_role("button", name="Сохранить")
    expect(save).to_be_enabled()
