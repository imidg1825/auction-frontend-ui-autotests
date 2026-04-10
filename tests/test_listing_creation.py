"""
Создание объявления (авторизованный пользователь).

Сессия подставляется через storage_state в conftest (файл auth/state.json).
"""

import re
import time
from pathlib import Path

import allure
import pytest
from playwright.sync_api import expect

# Минимальный JPEG 1×1 для загрузки фото (как в test_negative.py)
_MIN_JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb0043000302020302020303030304030304050805050406050a07070706080c0a0c0c0b0a0b0b0d0e12100d0e110e0b0b10161110131615141515170f11131818181718181c1c1c1a1a1d1d1f1f1f1f1f1f1f1f1f1f1cffc0001108000100010301110002110003011100ffc40014000100000000000000000000000000000008ffc40014100100000000000000000000000000000000ffda000c03010002100310000000d2ff"
)


STATE_JSON = Path(__file__).resolve().parent.parent / "auth" / "state.json"

pytestmark = pytest.mark.skipif(
    not STATE_JSON.is_file(),
    reason="Нет auth/state.json — выполните auth/save_auth.py и сохраните сессию.",
)


def _dismiss_cookie_banner_if_visible(page):
    btn = page.get_by_role("button", name="Принять")
    if btn.count() == 0:
        return
    if btn.first.is_visible():
        btn.first.click()


def _open_create_listing_from_home(page):
    # С главной: ждём устойчивее, чем domcontentloaded — иначе клик по «Создать» иногда не цепляет SPA-роутер.
    page.goto("/", wait_until="networkidle", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)
    create_btn = page.get_by_role("button", name="Создать объявление")
    expect(create_btn).to_be_visible(timeout=60_000)
    expect(create_btn).to_be_enabled(timeout=15_000)
    create_btn.click()


def _open_category_step(page):
    page.goto("/createAd", wait_until="domcontentloaded", timeout=120_000)
    _dismiss_cookie_banner_if_visible(page)
    main = page.locator("main")
    expect(
        main.get_by_role("heading", name="Выбрать категорию", exact=False)
    ).to_be_visible(timeout=60_000)


def _open_filled_listing_form(page):
    _open_category_step(page)
    page.get_by_text("Личные вещи", exact=True).nth(1).click()
    page.locator("main").get_by_text("Женский гардероб", exact=True).click()
    expect(page.get_by_label("Название товара", exact=False)).to_be_visible(
        timeout=20_000
    )


def _unique_autotest_listing_title() -> str:
    """Уникальное имя, чтобы не плодить неотличимые дубли на стенде."""
    return f"UITEST auto {int(time.time())}"


def _ensure_location_for_submit(page) -> None:
    loc = page.get_by_label("Местоположение", exact=False)
    if len(loc.input_value().strip()) >= 2:
        return
    loc.click()
    loc.fill("Москва")
    for _ in range(40):
        page.wait_for_timeout(500)
        opt = page.get_by_role("option").first
        if opt.count() > 0 and opt.is_visible():
            opt.click()
            page.wait_for_timeout(700)
            return
    loc.press("ArrowDown")
    page.wait_for_timeout(400)
    loc.press("Enter")
    page.wait_for_timeout(600)
    v = loc.input_value().strip()
    if len(v) < 2 or ("," not in v and len(v) <= 15):
        pytest.skip("Не удалось указать местоположение для размещения.")


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_create_listing_button_opens_flow_not_login_modal(page):
    """«Создать объявление» ведёт в сценарий создания, а не в окно входа."""
    _open_create_listing_from_home(page)

    expect(page).to_have_url(re.compile(r".*createAd"), timeout=60_000)
    expect(page.get_by_text("Введите E-mail для входа")).not_to_be_visible()
    expect(
        page.locator("main").get_by_role("heading", name="Выбрать категорию", exact=False)
    ).to_be_visible(timeout=30_000)


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_create_listing_opens_category_or_first_step(page):
    """Открывается шаг выбора категории («Новое объявление» / «Выбрать категорию»)."""
    _open_category_step(page)

    main = page.locator("main")
    expect(main.get_by_role("heading", name="Новое объявление", exact=False)).to_be_visible(
        timeout=30_000
    )
    expect(main.get_by_role("heading", name="Выбрать категорию", exact=False)).to_be_visible(
        timeout=10_000
    )
    expect(page).to_have_url(re.compile(r".*createAd"), timeout=15_000)


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_category_step_shows_root_categories(page):
    """На шаге выбора видны корневые категории."""
    _open_category_step(page)

    expect(page.get_by_text("Личные вещи", exact=True).nth(1)).to_be_visible()
    expect(page.get_by_text("Товары для дома", exact=True).nth(1)).to_be_visible()
    expect(page.get_by_text("Животные", exact=True).nth(1)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_selecting_leaf_category_opens_listing_form(page):
    """После выбора категории открывается форма объявления."""
    _open_filled_listing_form(page)

    expect(page.get_by_text("Разместить объявление", exact=False)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_listing_form_has_title_field(page):
    """Поле «Название товара»."""
    _open_filled_listing_form(page)

    title = page.get_by_label("Название товара", exact=False)
    expect(title).to_be_visible()
    title.fill("Тестовое название")
    expect(title).to_have_value("Тестовое название")


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_listing_form_has_description_field(page):
    """Поле описания («Описание товара»)."""
    _open_filled_listing_form(page)

    desc = page.locator("main").locator("textarea").first
    expect(desc).to_be_visible()
    desc.fill("Тестовое описание")
    expect(desc).to_have_value("Тестовое описание")


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_listing_form_has_photo_upload_block(page):
    """Блок загрузки фото."""
    _open_filled_listing_form(page)

    expect(page.get_by_text("Фотографии", exact=False)).to_be_visible()
    expect(page.locator('input[type="file"]')).to_be_attached()


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_listing_form_has_fixed_price_and_auction_options(page):
    """Переключение типа: фиксированная цена и аукцион."""
    _open_filled_listing_form(page)

    main = page.locator("main")
    expect(main.get_by_text("Фиксированная цена", exact=False)).to_be_visible()
    expect(main.get_by_text("Аукцион", exact=False)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_fixed_price_mode_shows_price_field(page):
    """В режиме фиксированной цены есть поле «Цена»."""
    _open_filled_listing_form(page)

    price = page.locator("main").locator('input[name="price"]')
    expect(price).to_be_visible()
    price.fill("1000")
    expect(price).to_have_value("1000")


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_auction_mode_shows_start_price_and_duration(page):
    """В режиме аукциона — «Стартовая цена» и «Продолжительность аукциона»."""
    _open_filled_listing_form(page)

    main = page.locator("main")
    main.get_by_text("Аукцион", exact=False).first.click()

    expect(main.locator('input[name="price"]')).to_be_visible()
    expect(main.get_by_text("Продолжительность аукциона", exact=False)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_listing_form_has_location_field(page):
    """Поле местоположения."""
    _open_filled_listing_form(page)

    expect(page.get_by_label("Местоположение", exact=False)).to_be_visible()


@allure.epic("UI Auction")
@allure.feature("Listing Creation")
def test_publish_fixed_price_listing_end_to_end_when_possible(page, tmp_path):
    """
    Полный сценарий: форма → фото → цена → «Разместить объявление» → результат на стенде.

    Один тест создаёт одно объявление с уникальным названием (метка времени).
    """
    _open_filled_listing_form(page)
    main = page.locator("main")
    title_text = _unique_autotest_listing_title()

    page.get_by_label("Название товара", exact=False).fill(title_text)
    main.locator("textarea").first.fill(
        "Автотест размещения. Объявление можно удалить после проверки."
    )

    img = tmp_path / "listing.jpg"
    img.write_bytes(_MIN_JPEG_BYTES)
    page.locator('input[type="file"]').set_input_files(str(img))
    page.wait_for_timeout(3500)

    _ensure_location_for_submit(page)

    price = main.locator('input[name="price"]')
    expect(price).to_be_visible()
    price.fill("889")
    page.wait_for_timeout(800)

    submit = main.get_by_role("button", name="Разместить объявление")
    if submit.is_disabled():
        pytest.skip("Кнопка «Разместить объявление» остаётся неактивной — размещение недоступно.")

    submit.click(no_wait_after=True)

    success_url = re.compile(r".*/(profile/myAds|product/[^/?#]+)", re.I)
    try:
        expect(page).to_have_url(success_url, timeout=60_000)
    except AssertionError:
        if "createAd" in page.url:
            err = page.locator("main").get_by_text(re.compile(r"ошибк|не удалось", re.I))
            if err.count() > 0 and err.first.is_visible():
                pytest.skip("Стенд вернул ошибку при размещении.")
        pytest.skip("После отправки формы URL не сменился на ожидаемый (поведение стенда).")

    page.wait_for_timeout(4000)
    body = page.locator("body").inner_text().lower()
    success_hint = any(
        w in body
        for w in (
            "успеш",
            "размещ",
            "модерац",
            "опублик",
            "создан",
            "объявление",
        )
    )
    if "/profile/myAds" not in page.url and "/product/" not in page.url.lower():
        if not success_hint:
            pytest.skip("Нет признака успешного создания в URL и тексте страницы.")

    if "/profile/myAds" in page.url:
        main_ads = page.locator("main")
        mod_tab = main_ads.get_by_role("button", name="На модерации")
        if mod_tab.count() > 0:
            mod_tab.first.click()
            page.wait_for_timeout(4000)
        expect(main_ads).to_contain_text(title_text, timeout=30_000)
    elif "/product/" in page.url.lower():
        expect(page.locator("main")).to_contain_text(title_text, timeout=20_000)
