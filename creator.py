"""
Playwright-автоматизация создания дашборда GetCourse.
Два режима: диагностика (разведка формы) и полное создание (11 виджетов).
"""
import asyncio
import os
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Page

DEBUG_DIR = os.path.join(os.path.dirname(__file__), "debug")
SCREENSHOTS = os.path.join(os.path.dirname(__file__), "screenshots")


async def _shot(page: Page, name: str, folder: str = None):
    target = folder or SCREENSHOTS
    os.makedirs(target, exist_ok=True)
    await page.screenshot(path=os.path.join(target, name))


async def _close_cookie(page: Page):
    try:
        await page.locator(
            'button:has-text("OK"), button:has-text("Ок"), button:has-text("Принять")'
        ).first.click(timeout=3000)
        await asyncio.sleep(0.4)
    except Exception:
        pass


async def _click_first_visible(page: Page, selectors: list[str], timeout: int = 5000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=timeout)
            await loc.click()
            return
        except Exception:
            continue
    raise Exception(f"Не найден ни один из элементов: {selectors}")


async def _find_first_visible(page: Page, selectors: list[str], timeout: int = 3000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            continue
    return None


# ── Логин ────────────────────────────────────────────────────────────────────

async def login(page: Page, gc_url: str, email: str, password: str, log_fn=print):
    log_fn("  Открываем страницу входа...")
    await page.goto(f"{gc_url}/cms/system/login", wait_until="load")
    await _shot(page, "1_login_page.png")
    await _close_cookie(page)

    await page.locator('input[name="email"], input[type="email"]').first.fill(email)
    await page.locator('input[name="password"], input[type="password"]').first.fill(password)
    await _shot(page, "2_filled.png")

    await page.click('button[type="submit"], input[type="submit"]')
    await asyncio.sleep(2)
    await page.wait_for_url(lambda url: "/cms/system/login" not in url, timeout=15000)
    await _shot(page, "3_after_login.png")
    log_fn("  Вход выполнен.")


# ── Создание нового дашборда ─────────────────────────────────────────────────

async def go_to_new_dashboard(page: Page, gc_url: str, log_fn=print):
    log_fn("  Открываем список дашбордов...")
    await page.goto(f"{gc_url}/pl/logic/funnel", wait_until="load")
    await asyncio.sleep(1.5)
    await _close_cookie(page)
    await _shot(page, "4_dashboard_list.png")

    log_fn("  Кликаем кнопку 'Создать дашборд'...")
    await _click_first_visible(page, [
        'button:has-text("Создать дашборд")',
        'a:has-text("Создать дашборд")',
        '[class*="btn"]:has-text("Создать дашборд")',
        ':has-text("Создать дашборд")',
    ], timeout=8000)
    await asyncio.sleep(2)
    await _shot(page, "5_new_dashboard_form.png")


async def set_dashboard_name(page: Page, gc_url: str, name: str, log_fn=print):
    log_fn("  Ищем поле для ввода названия...")
    await page.wait_for_selector(
        'input[type="text"]:visible, input:not([type="hidden"]):visible',
        timeout=15000,
    )
    await asyncio.sleep(0.5)

    inp = await _find_first_visible(page, [
        'input[placeholder*="назван"]',
        'input[placeholder*="Назван"]',
        'input[placeholder*="дашборд"]',
        '[class*="modal"]:visible input[type="text"]',
        '[class*="dialog"]:visible input[type="text"]',
        '[class*="popup"]:visible input[type="text"]',
        'td input[type="text"]',
        'input[type="text"]',
        'input:not([type="hidden"]):not([type="password"]):not([type="email"])',
    ], timeout=5000)

    if inp is None:
        await _shot(page, "error_no_input.png")
        raise Exception("Не найдено поле для ввода названия дашборда")

    await inp.clear()
    await inp.fill(name)
    await asyncio.sleep(0.3)
    log_fn(f"  Введено название: {name}")

    saved = False
    for btn_text in ["Создать", "Сохранить", "OK", "Ок", "Подтвердить"]:
        try:
            await page.locator(f'button:has-text("{btn_text}")').first.click(timeout=3000)
            saved = True
            log_fn(f"  Нажата кнопка '{btn_text}'.")
            break
        except Exception:
            continue

    if not saved:
        log_fn("  Кнопка не найдена — нажимаем Enter.")
        await inp.press("Enter")

    log_fn("  Ожидаем загрузки страницы дашборда...")
    await page.wait_for_selector(
        'button:has-text("Добавить блок"), a:has-text("Добавить блок")',
        timeout=25000,
    )
    await asyncio.sleep(1)
    await _shot(page, "6_dashboard_created.png")
    log_fn("  Дашборд создан.")


# ── Диагностика формы виджета ────────────────────────────────────────────────

async def _dump_elements(page: Page, filename: str, log_fn=print):
    """Сохраняет скриншот + список видимых элементов формы."""
    await page.screenshot(
        path=os.path.join(DEBUG_DIR, filename + ".png"), full_page=False)

    elements = await page.evaluate("""() => {
        const result = [];
        document.querySelectorAll('input, select, textarea, button, label').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                result.push({
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    name: el.name || '',
                    id: el.id || '',
                    placeholder: el.placeholder || '',
                    className: el.className.substring(0, 100) || '',
                    text: (el.innerText || el.value || '').substring(0, 60),
                    options: el.tagName === 'SELECT'
                        ? Array.from(el.options).map(o => o.text).slice(0, 30)
                        : []
                });
            }
        });
        return result;
    }""")

    lines = [f"Найдено {len(elements)} видимых элементов\n", "=" * 60 + "\n"]
    for el in elements:
        lines.append(
            f"\n<{el['tag']}>"
            f"\n  type        = {el['type']!r}"
            f"\n  name        = {el['name']!r}"
            f"\n  id          = {el['id']!r}"
            f"\n  placeholder = {el['placeholder']!r}"
            f"\n  text        = {el['text']!r}"
            f"\n  class       = {el['className']!r}"
        )
        if el["options"]:
            lines.append(f"\n  options     = {el['options']}")
        lines.append("\n")

    with open(os.path.join(DEBUG_DIR, filename + ".txt"), "w", encoding="utf-8") as f:
        f.writelines(lines)
    log_fn(f"  Сохранено: debug/{filename}.png + debug/{filename}.txt ({len(elements)} эл.)")


async def explore_widget_form(page: Page, log_fn=print):
    """
    Нажимает 'Добавить блок', затем проходит 3 шага:
    1. Начальное состояние формы
    2. После выбора 'Пользователи'
    3. После выбора 'Заказы'
    Сохраняет скриншоты и списки элементов в debug/.
    """
    os.makedirs(DEBUG_DIR, exist_ok=True)

    log_fn("  Ищем кнопку 'Добавить блок'...")
    await _shot(page, "before_add_widget.png", DEBUG_DIR)

    await _click_first_visible(page, [
        'button:has-text("Добавить блок")',
        'a:has-text("Добавить блок")',
        ':has-text("Добавить блок")',
    ], timeout=10000)

    log_fn("  Ждём загрузки формы...")
    await page.wait_for_selector('input.title-input', timeout=10000)
    await asyncio.sleep(1)

    log_fn("  Шаг 1: начальное состояние формы")
    await _dump_elements(page, "step1_initial", log_fn)

    log_fn("  Шаг 2: выбираем 'Пользователи'...")
    await page.locator('select.context-selector').select_option(label='Пользователи')
    await asyncio.sleep(2)
    await _dump_elements(page, "step2_users", log_fn)

    log_fn("  Шаг 2.5: проверяем фильтры (группа, UTM, Max, TG-бот)...")
    for filter_type, label in [
        ("in_segment_rule",                      "group"),
        ("UserContext_formfieldvalue",            "utm"),
        ("user_max_connected",                   "max"),
        ("user_telegram_specified_bot_connected", "tgbot"),
    ]:
        await page.click('button[data-toggle="dropdown"]:has-text("Добавить условие")')
        await asyncio.sleep(0.7)
        await page.click(f'li[data-type="{filter_type}"] a')
        await asyncio.sleep(1.5)
        await _dump_elements(page, f"filter_{label}", log_fn)

    log_fn("  Шаг 3: выбираем 'Заказы'...")
    await page.locator('select.context-selector').select_option(label='Заказы')
    await asyncio.sleep(2)
    await _dump_elements(page, "step3_orders", log_fn)

    html = await page.content()
    with open(os.path.join(DEBUG_DIR, "widget_form.html"), "w", encoding="utf-8") as f:
        f.write(html)

    log_fn("  ✓ Диагностика завершена. Файлы в папке debug/")
    log_fn("  ВАЖНО: дашборд 'ДИАГНОСТИКА_УДАЛИТЬ' нужно удалить вручную в GetCourse.")


# ── Работа с виджетами ───────────────────────────────────────────────────────

async def open_add_widget(page: Page):
    await _click_first_visible(page, [
        'button:has-text("Добавить блок")',
        'a:has-text("Добавить блок")',
        ':has-text("Добавить блок")',
    ], timeout=8000)
    await page.wait_for_selector('input.title-input', timeout=12000)
    await asyncio.sleep(1.0)


async def set_widget_title(page: Page, title: str):
    inp = await _find_first_visible(page, [
        'input.title-input',
        'input[placeholder="Название сегмента"]',
    ])
    if inp:
        await inp.click()
        await asyncio.sleep(0.2)
        await inp.clear()
        await inp.fill(title)
        await asyncio.sleep(0.2)


async def select_source(page: Page, source: str):
    sel = page.locator('select.context-selector').first
    await sel.wait_for(state="visible", timeout=8000)
    await sel.select_option(label=source)
    # принудительно вызываем change — на случай если значение уже было выбрано
    await sel.dispatch_event('change')
    await asyncio.sleep(2.0)


async def select_date_field(page: Page, label: str):
    try:
        await page.locator('.date-selector-wrapper select.form-control').select_option(label=label)
    except Exception:
        try:
            await page.locator('select.form-control').nth(1).select_option(label=label)
        except Exception:
            pass


async def _open_filter_dropdown(page: Page, filter_type: str):
    """Открывает дропдаун 'Добавить условие' и выбирает тип фильтра."""
    btn = page.locator('button[data-toggle="dropdown"]:has-text("Добавить условие")')
    await btn.scroll_into_view_if_needed()
    await btn.click()
    await asyncio.sleep(0.5)
    await page.locator(f'li[data-type="{filter_type}"] a').click()
    await asyncio.sleep(1.2)


async def _open_last_select2(page: Page):
    loc = page.locator('.rules-container .select2-container').last
    await loc.scroll_into_view_if_needed()
    await asyncio.sleep(0.3)
    await loc.click(timeout=6000)
    await asyncio.sleep(0.8)


async def _select2_pick(page: Page, value: str):
    """Выбирает значение из открытого Select2-дропдауна."""
    # Пробуем напечатать в поле поиска (короткий таймаут — не блокирует)
    try:
        inp = page.locator('input.select2-input:visible').first
        await inp.wait_for(state="visible", timeout=3000)
        await inp.fill("")
        await inp.type(value, delay=70)
        await asyncio.sleep(2.0)
    except Exception:
        pass

    # Ищем пункт с нужным текстом
    try:
        result = page.locator(f'.select2-results li:visible:has-text("{value}")').first
        await result.wait_for(state="visible", timeout=6000)
        await result.click()
        await asyncio.sleep(0.8)
        return
    except Exception:
        pass

    # Запасной вариант — первый видимый пункт
    result = page.locator('.select2-results .select2-result-selectable:visible').first
    await result.wait_for(state="visible", timeout=6000)
    await result.click()
    await asyncio.sleep(0.8)


async def set_group_filter(page: Page, group_name: str, log_fn=print):
    log_fn(f"      → добавляем условие 'В группе'...")
    await _open_filter_dropdown(page, "user_ingrouprule")
    log_fn(f"      → открываем Select2...")
    await _open_last_select2(page)
    log_fn(f"      → ищем группу: {group_name}")
    await _select2_pick(page, group_name)
    log_fn(f"      → готово.")


async def set_offer_filter(page: Page, offer_name: str):
    await _open_filter_dropdown(page, "deal_offer_id")
    await _open_last_select2(page)
    await _select2_pick(page, offer_name)


async def set_max_filter(page: Page):
    await _open_filter_dropdown(page, "user_max_connected")
    await _click_first_visible(page, [
        '.rules-container label:has-text("Да") input',
        '.rules-container input[value="1"]',
        '.rules-container input[value="yes"]',
    ], timeout=4000)


async def set_tg_bot_filter(page: Page, bot_name: str):
    await _open_filter_dropdown(page, "user_telegram_specified_bot_connected")
    await page.locator('.rules-container .select2-container').last.click()
    await asyncio.sleep(0.4)
    await _select2_pick(page, bot_name)


async def set_utm_filter(page: Page, field_name: str, value: str, context: str = "UserContext"):
    await _open_filter_dropdown(page, f"{context}_formfieldvalue")
    await asyncio.sleep(0.5)
    try:
        await page.locator('.rules-container select').last.select_option(value=field_name)
        await asyncio.sleep(0.5)
    except Exception:
        try:
            await page.locator('.rules-container .select2-container').last.click()
            await asyncio.sleep(0.4)
            await _select2_pick(page, field_name)
        except Exception:
            pass
    try:
        await page.locator(
            '.rules-container input[type="text"]:not(.title-input)'
        ).last.fill(value)
    except Exception:
        pass


async def set_date_range(page: Page, date_from: str, date_to: str):
    inputs = page.locator('.sample-date-field input[placeholder]')
    count = await inputs.count()
    if count >= 2:
        await inputs.nth(0).fill(date_from)
        await inputs.nth(1).fill(date_to)
    elif count == 1:
        await inputs.nth(0).fill(date_from)


async def save_widget(page: Page):
    await asyncio.sleep(0.5)
    await _click_first_visible(page, [
        '.modal-footer button.btn-success',
        '.modal-footer button:has-text("Сохранить")',
        'button.btn-success:has-text("Сохранить")',
    ], timeout=8000)
    await page.wait_for_selector('input.title-input', state="hidden", timeout=10000)
    await asyncio.sleep(1.5)


async def save_dashboard(page: Page):
    await _click_first_visible(page, [
        'button:has-text("Сохранить дашборд")',
        'a:has-text("Сохранить дашборд")',
        'button:has-text("Сохранить")',
    ], timeout=8000)
    await asyncio.sleep(1)


# ── 11 виджетов ──────────────────────────────────────────────────────────────

async def widget_registrations_total(page: Page, tag: str, log_fn=print):
    log_fn("    форма открывается...")
    await open_add_widget(page)
    log_fn("    заполняем тайтл...")
    await set_widget_title(page, "Регистрации всего")
    log_fn("    выбираем источник...")
    await select_source(page, "Пользователи")
    log_fn("    ставим фильтр группы...")
    await set_group_filter(page, f"[{tag}] Регистрация на вебинар", log_fn)
    log_fn("    сохраняем виджет...")
    await save_widget(page)


async def widget_paid(page: Page, tag: str, offer_name: str, log_fn=print):
    log_fn("    форма открывается...")
    await open_add_widget(page)
    log_fn("    заполняем тайтл...")
    await set_widget_title(page, "Платное участие")
    log_fn("    выбираем источник...")
    await select_source(page, "Заказы")
    log_fn("    выбираем поле даты...")
    await select_date_field(page, "Дата создания заказа")
    log_fn("    ставим фильтр предложения...")
    await set_offer_filter(page, offer_name)
    log_fn("    сохраняем виджет...")
    await save_widget(page)


async def widget_max(page: Page, tag: str, log_fn=print):
    log_fn("    форма открывается...")
    await open_add_widget(page)
    log_fn("    заполняем тайтл...")
    await set_widget_title(page, "Зашли в max")
    log_fn("    выбираем источник...")
    await select_source(page, "Пользователи")
    log_fn("    выбираем поле даты...")
    await select_date_field(page, "Дата создания")
    log_fn("    ставим фильтр группы...")
    await set_group_filter(page, f"[{tag}] Регистрация на вебинар", log_fn)
    log_fn("    ставим фильтр Max...")
    await set_max_filter(page)
    log_fn("    сохраняем виджет...")
    await save_widget(page)


async def widget_visits(page: Page, tag: str, log_fn=print):
    log_fn("    форма открывается...")
    await open_add_widget(page)
    log_fn("    заполняем тайтл...")
    await set_widget_title(page, "Посещения всего")
    log_fn("    выбираем источник...")
    await select_source(page, "Пользователи")
    await _shot(page, "w2_after_source.png")
    log_fn("    выбираем поле даты...")
    await select_date_field(page, "Дата создания")
    log_fn("    ставим фильтр группы...")
    await set_group_filter(page, f"[{tag}] Посещение", log_fn)
    log_fn("    сохраняем виджет...")
    await save_widget(page)


async def widget_bot(page: Page, tag: str, tg_bot: str):
    await open_add_widget(page)
    await set_widget_title(page, "подключен бот")
    await select_source(page, "Пользователи")
    await set_group_filter(page, f"[{tag}] Регистрация на вебинар")
    await set_tg_bot_filter(page, tg_bot)
    await save_widget(page)


async def widget_banner(page: Page, tag: str):
    await open_add_widget(page)
    await set_widget_title(page, "С баннера")
    await select_source(page, "Пользователи")
    await select_date_field(page, "Дата создания")
    await set_utm_filter(page, "utm_content_c", "banner")
    await set_group_filter(page, f"[{tag}] Регистрация на вебинар")
    await save_widget(page)


async def widget_pokoi(page: Page, tag: str):
    await open_add_widget(page)
    await set_widget_title(page, "Регистрации ТГ анонс Покои")
    await select_source(page, "Пользователи")
    await select_date_field(page, "Дата создания")
    await set_utm_filter(page, "utm_medium_c", "pokoi")
    await set_utm_filter(page, "utm_content_c", "announce")
    await set_group_filter(page, f"[{tag}] Регистрация на вебинар")
    await save_widget(page)


async def widget_zerocoder(page: Page, tag: str):
    await open_add_widget(page)
    await set_widget_title(page, "Регистрации ТГ анонс Зерокодер")
    await select_source(page, "Пользователи")
    await select_date_field(page, "Дата создания")
    await set_utm_filter(page, "utm_medium_c", "channel_oqode")
    await set_utm_filter(page, "utm_content_c", "announce")
    await set_group_filter(page, f"[{tag}] Регистрация на вебинар")
    await save_widget(page)


async def widget_buttons(page: Page, tag: str):
    await open_add_widget(page)
    await set_widget_title(page, "Регистрации с кнопок")
    await select_source(page, "Пользователи")
    await select_date_field(page, "Дата создания")
    await set_utm_filter(page, "utm_source_c", "telegram")
    await set_utm_filter(page, "utm_medium_c", "miniapp")
    await set_group_filter(page, f"[{tag}] Регистрация на вебинар")
    await save_widget(page)


async def widget_speaker(page: Page, tag: str, speaker_utm: str):
    await open_add_widget(page)
    await set_widget_title(page, "Регистрации с канала спикера")
    await select_source(page, "Пользователи")
    await select_date_field(page, "Дата создания")
    await set_utm_filter(page, "utm_medium_c", speaker_utm)
    await set_group_filter(page, f"[{tag}] Регистрация на вебинар")
    await save_widget(page)


async def widget_orders(page: Page, tag: str, date_from: str, date_to: str):
    await open_add_widget(page)
    await set_widget_title(page, "Заказы")
    await select_source(page, "Заказы")
    await select_date_field(page, "Дата создания заказа")
    await set_utm_filter(page, "utm_campaign_c", tag, context="DealContext")
    await set_date_range(page, date_from, date_to)
    await save_widget(page)


# ── Диагностический запуск ───────────────────────────────────────────────────

async def diagnostic_run(gc_url: str, email: str, password: str, log_fn=print):
    """Логин → тестовый дашборд → разведка формы виджета → стоп."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            log_fn("=== РЕЖИМ ДИАГНОСТИКИ ===")
            log_fn("Цель: узнать как выглядит форма добавления виджета.")
            await login(page, gc_url, email, password, log_fn)
            await go_to_new_dashboard(page, gc_url, log_fn)
            await set_dashboard_name(page, gc_url, "ДИАГНОСТИКА_УДАЛИТЬ", log_fn)
            await explore_widget_form(page, log_fn)
        except Exception as e:
            await _shot(page, "diag_error.png", DEBUG_DIR)
            log_fn(f"✗ Ошибка диагностики: {e}")
        finally:
            await browser.close()


def run_diagnostic(gc_url, email, password, log_fn=print):
    asyncio.run(diagnostic_run(gc_url, email, password, log_fn))


# ── Полный запуск ─────────────────────────────────────────────────────────────

async def create_dashboard(
    gc_url: str, email: str, password: str,
    tag: str, webinar_date: datetime,
    offer_name: str, speaker_utm: str, tg_bot: str,
    log_fn=print, ready_fn=None,
):
    date_from = webinar_date.strftime("%d.%m.%Y 00:00")
    date_to = (webinar_date + timedelta(days=62)).strftime("%d.%m.%Y 23:59")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await login(page, gc_url, email, password, log_fn)
            await go_to_new_dashboard(page, gc_url, log_fn)
            await set_dashboard_name(page, gc_url, f"Вебинар [{tag}]", log_fn)

            steps = [
                ("Регистрации всего",  widget_registrations_total(page, tag, log_fn)),
                ("Посещения всего",    widget_visits(page, tag, log_fn)),
                ("Платное участие",    widget_paid(page, tag, offer_name, log_fn)),
            ]

            for name, coro in steps:
                log_fn(f"  → Виджет: {name}")
                await coro
                await _shot(page, f"widget_{name[:20].replace(' ', '_')}.png")

            await save_dashboard(page)
            await _shot(page, "final_dashboard.png")
            log_fn("✓ Готово! Дашборд создан. Браузер открыт для проверки.")
        except Exception as e:
            await _shot(page, "error.png")
            log_fn(f"✗ Ошибка: {e}")
        finally:
            if ready_fn:
                ready_fn()
            log_fn("Кнопка разблокирована — можно создавать следующий дашборд.")
            await asyncio.Event().wait()


def run(gc_url, email, password, tag, webinar_date, offer_name, speaker_utm, tg_bot,
        log_fn=print, ready_fn=None):
    asyncio.run(create_dashboard(
        gc_url, email, password, tag, webinar_date, offer_name, speaker_utm, tg_bot,
        log_fn, ready_fn
    ))
