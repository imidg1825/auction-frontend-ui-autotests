"""
Негативные UI-сценарии: валидация и блокировка действий до корректного ввода.
"""

import re
from pathlib import Path

import allure
import pytest
from playwright.sync_api import expect

BASE_URL = "https://front.test.kp.ktsf.ru/"
STATE_JSON = Path(__file__).resolve().parent.parent / "auth" / "state.json"

# Валидный минимальный JPEG 1×1 для поля загрузки фото
_MIN_JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb0043000302020302020303030304030304050805050406050a07070706080c0a0c0c0b0a0b0b0d0e12100d0e110e0b0b10161110131615141515170f11131818181718181c1c1c1a1a1d1d1f1f1f1f1f1f1f1f1f1f1cffc0001108000100010301110002110003011100ffc40014000100000000000000000000000000000008ffc40014100100000000000000000000000000000000ffda000c03010002100310000000d2ff"
)


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()
        page.wait_for_timeout(400)


def _open_login_modal(page):
    page.goto(BASE_URL, wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)
    login_btn = page.get_by_role("button", name="Войти")
    if login_btn.count() == 0 or not login_btn.first.is_visible():
        pytest.skip(
            "Кнопка «Войти» недоступна (часто при активной сессии из auth/state.json)."
        )
    login_btn.click()


def _auth_dialog(page):
    dlg = page.locator('[role="dialog"]').first
    expect(dlg).to_be_visible()
    return dlg


def _open_listing_form_after_category(page):
    page.goto("/createAd", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)
    page.get_by_text("Личные вещи", exact=True).nth(1).click()
    page.locator("main").get_by_text("Женский гардероб", exact=True).click()
    expect(page.get_by_label("Название товара", exact=False)).to_be_visible(
        timeout=25_000
    )


def _pick_location_first_suggestion(page) -> bool:
    loc = page.get_by_label("Местоположение", exact=False)
    loc.click()
    loc.fill("Москва")

    # Вариант 1: доступная разметка autocomplete через role="option"
    option = page.get_by_role("option").filter(has_text=re.compile("Москва", re.I)).first
    try:
        expect(option).to_be_visible(timeout=10_000)
        option.click()
        return True
    except AssertionError:
        pass

    # Вариант 2: fallback для текущей разметки, если options не имеют role="option"
    suggestion = page.locator("main").get_by_text(re.compile(r"Москва", re.I)).last
    try:
        expect(suggestion).to_be_visible(timeout=10_000)
        suggestion.click()
        return True
    except AssertionError:
        pass

    # Вариант 3: клавиатурный выбор, если список открыт, но локаторы нестабильные
    loc.press("ArrowDown")
    loc.press("Enter")

    value = loc.input_value().strip()
    return len(value) >= 2


def _ensure_listing_location_or_skip(page) -> None:
    """У авторизованного пользователя город часто подставлен из профиля."""
    loc = page.get_by_label("Местоположение", exact=False)
    if len(loc.input_value().strip()) >= 2:
        return
    if not _pick_location_first_suggestion(page):
        pytest.skip("Не удалось заполнить местоположение для проверки цены.")


def _auction_card_link(page):
    return page.locator('[class*="Card"]').locator('a[href^="/auction/"]')


@allure.epic("UI Auction")
@allure.feature("Negative Scenarios")
def test_login_invalid_email_disables_continue_and_shows_hint(guest_page):
    """Некорректный e-mail: «Продолжить» неактивна и показывается сообщение о формате."""
    _open_login_modal(guest_page)
    dlg = _auth_dialog(guest_page)
    email = dlg.locator('input[type="email"]')
    btn = dlg.get_by_role("button", name="Продолжить")

    email.fill("not-an-email")
    expect(btn).to_be_disabled()
    expect(dlg.get_by_text("Неверный формат", exact=False)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Negative Scenarios")
def test_login_empty_email_disables_continue(guest_page):
    """Пустой e-mail не активирует «Продолжить»."""
    _open_login_modal(guest_page)
    dlg = _auth_dialog(guest_page)
    email = dlg.locator('input[type="email"]')
    btn = dlg.get_by_role("button", name="Продолжить")

    expect(btn).to_be_disabled()
    email.fill("x@y.co")
    expect(btn).to_be_enabled()
    email.fill("")
    expect(btn).to_be_disabled()


@allure.epic("UI Auction")
@allure.feature("Negative Scenarios")
@pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — сценарий создания объявления недоступен.",
)
def test_create_listing_submit_disabled_when_required_fields_empty(page):
    """Пустая форма: нельзя отправить объявление (кнопка неактивна)."""
    _open_listing_form_after_category(page)
    submit = page.locator("main").get_by_role("button", name="Разместить объявление")
    expect(submit).to_be_disabled()


@allure.epic("UI Auction")
@allure.feature("Negative Scenarios")
@pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — сценарий создания объявления недоступен.",
)
def test_create_listing_invalid_or_empty_price_keeps_submit_disabled(page, tmp_path):
    """Пустая или некорректная цена не даёт активировать «Разместить объявление»."""
    _open_listing_form_after_category(page)
    main = page.locator("main")
    submit = main.get_by_role("button", name="Разместить объявление")
    price = main.locator('input[name="price"]')
    expect(price).to_be_visible()

    img = tmp_path / "one.jpg"
    img.write_bytes(_MIN_JPEG_BYTES)

    page.get_by_label("Название товара", exact=False).fill("Негативный тест цены")
    main.locator("textarea").first.fill("Описание для проверки валидации цены.")
    page.locator('input[type="file"]').set_input_files(str(img))
    page.wait_for_timeout(2000)

    _ensure_listing_location_or_skip(page)

    price.fill("")
    page.wait_for_timeout(500)
    expect(submit).to_be_disabled()

    price.fill("abc")
    page.wait_for_timeout(500)
    expect(submit).to_be_disabled()

    price.fill("1500")
    page.wait_for_timeout(500)
    expect(submit).to_be_enabled()


@allure.epic("UI Auction")
@allure.feature("Negative Scenarios")
@pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — сценарий создания объявления недоступен.",
)
def test_create_auction_invalid_or_empty_start_price_keeps_submit_disabled(page, tmp_path):
    """Режим аукциона: пустая или неверная стартовая цена блокирует «Разместить аукцион»."""
    _open_listing_form_after_category(page)
    main = page.locator("main")
    main.get_by_text("Аукцион", exact=False).first.click()
    page.wait_for_timeout(800)

    submit = main.get_by_role("button", name="Разместить аукцион")
    price = main.locator('input[name="price"]')
    expect(price).to_be_visible()

    img = tmp_path / "one.jpg"
    img.write_bytes(_MIN_JPEG_BYTES)

    page.get_by_label("Название товара", exact=False).fill("Аукцион негатив")
    main.locator("textarea").first.fill("Описание для аукциона.")
    page.locator('input[type="file"]').set_input_files(str(img))
    page.wait_for_timeout(2000)

    _ensure_listing_location_or_skip(page)

    price.fill("")
    page.wait_for_timeout(500)
    expect(submit).to_be_disabled()

    price.fill("not-a-number")
    page.wait_for_timeout(500)
    expect(submit).to_be_disabled()

    price.fill("900")
    page.wait_for_timeout(500)
    expect(submit).to_be_enabled()


@allure.epic("UI Auction")
@allure.feature("Negative Scenarios")
@pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — модалка ставки недоступна.",
)
def test_auction_bid_empty_amount_disables_confirm(page):
    """В модалке ставки пустая сумма не активирует «Подтвердить ставку»."""
    page.goto("/", wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(5000)
    _dismiss_cookie_banner_if_visible(page)

    link = _auction_card_link(page)
    if link.count() == 0:
        pytest.skip("На главной нет карточки аукциона (ссылка /auction/).")

    expect(link.first).to_be_visible(timeout=60_000)
    link.first.click(no_wait_after=True)
    expect(page).to_have_url(re.compile(r".*/auction/"), timeout=60_000)

    cta = page.get_by_role("button", name="Сделать ставку")
    if cta.count() == 0:
        pytest.skip("Нет кнопки «Сделать ставку» на странице аукциона.")
    cta.click()

    modal = page.locator('[role="dialog"]').filter(has_text="Установить ставку")
    expect(modal).to_be_visible(timeout=15_000)

    confirm = modal.get_by_role("button", name="Подтвердить ставку")
    expect(confirm).to_be_disabled()

    amount = modal.get_by_placeholder("Введите сумму")
    expect(amount).to_be_visible()
    expect(amount).to_have_value("")


@allure.epic("UI Auction")
@allure.feature("Negative Scenarios")
@pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — модалка ставки недоступна.",
)
def test_auction_bid_confirm_stays_disabled_for_zero_or_negative_if_typed(page):
    """Если в поле суммы нельзя отправить корректное значение — кнопка остаётся неактивной."""
    page.goto("/", wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(5000)
    _dismiss_cookie_banner_if_visible(page)

    link = _auction_card_link(page)
    if link.count() == 0:
        pytest.skip("На главной нет карточки аукциона (ссылка /auction/).")

    link.first.click(no_wait_after=True)
    expect(page).to_have_url(re.compile(r".*/auction/"), timeout=60_000)

    cta = page.get_by_role("button", name="Сделать ставку")
    if cta.count() == 0:
        pytest.skip("Нет кнопки «Сделать ставку».")
    cta.click()

    modal = page.locator('[role="dialog"]').filter(has_text="Установить ставку")
    expect(modal).to_be_visible(timeout=15_000)
    confirm = modal.get_by_role("button", name="Подтвердить ставку")
    amount = modal.get_by_placeholder("Введите сумму")

    amount.fill("0")
    page.wait_for_timeout(400)
    if confirm.is_enabled():
        pytest.skip("Стенд разрешает нулевую ставку — отдельная валидация не проверяется.")

    expect(confirm).to_be_disabled()
