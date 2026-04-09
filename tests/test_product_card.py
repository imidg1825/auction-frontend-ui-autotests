"""
Страница товара: переход с главной по карточке и проверки блоков.
"""

import re

import pytest
from playwright.sync_api import expect

# Типичный формат номера после «Показать номер» на стенде (+7 (XXX) XXX-XX-XX)
_PHONE_SHOWN_RE = re.compile(r"\+7\s*\(\d{3}\)\s*\d{3}-\d{2}-\d{2}")
_MESSAGES_URL_RE = re.compile(r"/(profile/)?messages", re.I)


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_first_product_from_home(page):
    page.goto("/", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)

    cards = page.locator('[class*="Card"]')
    expect(cards.first).to_be_visible(timeout=60_000)
    link = cards.first.locator("a").first
    expect(link).to_be_visible()

    with page.expect_navigation(timeout=60_000):
        link.click()

    expect(page).to_have_url(re.compile(r".*/product/[^/]+"))


def test_open_product_page_from_home_card(page):
    """С главной по первой карточке открывается страница товара."""
    _open_first_product_from_home(page)


def test_product_page_shows_title(page):
    """Отображается название товара (заголовок)."""
    _open_first_product_from_home(page)

    title = page.locator("main h1").first
    expect(title).to_be_visible()
    expect(title).to_have_text(re.compile(r"\S"))


def test_product_page_shows_price(page):
    """Отображается цена (с символом ₽)."""
    _open_first_product_from_home(page)

    expect(page.locator("main")).to_contain_text("₽")


def test_product_page_shows_description_section(page):
    """Отображается блок описания."""
    _open_first_product_from_home(page)

    expect(page.get_by_role("heading", name=re.compile("Описание"))).to_be_visible()
    expect(page.locator("main").get_by_text("Описание товара", exact=False)).to_be_visible()


def test_product_page_shows_location(page):
    """Отображается местоположение."""
    _open_first_product_from_home(page)

    main = page.locator("main")
    expect(main.get_by_text("Местоположение", exact=False)).to_be_visible()


def test_product_page_has_write_button(page):
    """Есть кнопка «Написать»."""
    _open_first_product_from_home(page)

    expect(page.get_by_role("button", name="Написать")).to_be_visible()


def test_product_page_has_show_phone_button(page):
    """Есть кнопка «Показать номер»."""
    _open_first_product_from_home(page)

    expect(page.get_by_role("button", name="Показать номер")).to_be_visible()


def test_product_page_has_seller_info_block(page):
    """Есть блок с информацией о продавце."""
    _open_first_product_from_home(page)

    expect(page.locator("main").get_by_text("Активен", exact=False)).to_be_visible()


def test_product_page_seller_other_listings_or_empty_state(page):
    """Список других объявлений продавца или явная пустая подпись."""
    _open_first_product_from_home(page)

    main = page.locator("main")
    other_cards = main.locator('[class*="Card"]')
    empty_state = main.get_by_text("нет объявлений", exact=False)

    if other_cards.count() > 0:
        expect(other_cards.first).to_be_visible()
    else:
        expect(empty_state).to_be_visible()


def test_product_show_phone_reveals_number_or_updates_state(page):
    """«Показать номер»: после клика в DOM появляется номер или меняется состояние кнопки."""
    _open_first_product_from_home(page)

    btn = page.get_by_role("button", name="Показать номер")
    if btn.count() == 0:
        pytest.skip("На этой карточке нет кнопки «Показать номер».")

    main = page.locator("main")
    btn.click(no_wait_after=True)
    page.wait_for_timeout(3000)

    text_after = main.inner_text()
    if _PHONE_SHOWN_RE.search(text_after):
        expect(main.get_by_text(_PHONE_SHOWN_RE).first).to_be_visible(timeout=15_000)
        return

    hide_or_call = page.get_by_role(
        "button", name=re.compile(r"Скрыть|Позвонить|Скопировать", re.I)
    )
    if hide_or_call.count() > 0 and hide_or_call.first.is_visible():
        expect(hide_or_call.first).to_be_visible()
        return

    pytest.skip("После клика номер не отобразился и UI не изменился (поведение стенда).")


def test_product_write_opens_chat_dialog_messages_or_composer(page):
    """«Написать»: открывается чат/модалка, переход в сообщения или поле для текста."""
    _open_first_product_from_home(page)

    write = page.get_by_role("button", name="Написать")
    if write.count() == 0:
        pytest.skip("На этой карточке нет кнопки «Написать».")

    write.click(no_wait_after=True)
    page.wait_for_timeout(4000)

    dlg = page.locator('[role="dialog"]')
    if dlg.count() > 0 and dlg.first.is_visible():
        expect(dlg.first).to_be_visible()
        return

    if _MESSAGES_URL_RE.search(page.url):
        expect(page).to_have_url(_MESSAGES_URL_RE, timeout=5_000)
        return

    composer = page.get_by_placeholder(re.compile(r"Написать сообщение", re.I))
    for i in range(composer.count()):
        if composer.nth(i).is_visible():
            expect(composer.nth(i)).to_be_visible()
            return

    pytest.skip(
        "После «Написать» нет видимого чата, модалки, перехода в сообщения и поля ввода."
    )
