import random
import re

from playwright.sync_api import expect


BASE_URL = "https://front.test.kp.ktsf.ru/"


def test_home_page_opens(page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120_000)
    expect(page).to_have_url(re.compile(r"https://front\.test\.kp\.ktsf\.ru/?"))
    expect(page).to_have_title(re.compile(r"\S"))


def test_header_has_create_listing_button(page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120_000)
    btn = page.get_by_role("button", name="Создать объявление")
    expect(btn).to_be_visible()


def test_header_has_login_button_for_guest(guest_page):
    guest_page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120_000)
    btn = guest_page.get_by_role("button", name="Войти")
    expect(btn).to_be_visible()


def test_header_has_all_categories_button(page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120_000)
    btn = page.get_by_role("button", name="Все категории")
    expect(btn).to_be_visible()


def test_header_has_search_field(page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120_000)
    search = page.get_by_placeholder("Поиск по объявлениям")
    expect(search).to_be_visible()


def test_home_shows_listing_cards(page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120_000)
    cards = page.locator('[class*="Card"]')
    expect(cards.first).to_be_visible(timeout=60_000)
    assert cards.count() >= 2


def test_click_random_card_opens_product_page(page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120_000)
    cards = page.locator('[class*="Card"]')
    expect(cards.first).to_be_visible(timeout=60_000)
    n = cards.count()
    assert n >= 1

    i = random.randrange(n)
    link = cards.nth(i).locator("a").first
    expect(link).to_be_visible()
    link.click()
    # Случайная карточка может вести на /product/ или /auction/.
    expect(page).to_have_url(
        re.compile(r"/(product|auction)/", re.I),
        timeout=45_000,
    )
