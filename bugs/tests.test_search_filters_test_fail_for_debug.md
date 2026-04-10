# test_fail_for_debug

## Источник
- Тест: tests.test_search_filters::test_fail_for_debug

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
AssertionError: Тестовое падение для проверки автоскрина и баг-репорта
assert False

def test_fail_for_debug():
>       assert False, "Тестовое падение для проверки автоскрина и баг-репорта"
E       AssertionError: Тестовое падение для проверки автоскрина и баг-репорта
E       assert False

tests\test_search_filters.py:298: AssertionError
```
## Окружение
- Стенд: https://front.test.kp.ktsf.ru/
- Браузер: Chromium
- Источник: автогенерация из pytest junit.xml

## Примечание
Черновик создан автоматически после failed-прогона.
