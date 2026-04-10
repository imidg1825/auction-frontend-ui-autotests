import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    auth_check = subprocess.run([sys.executable, "-m", "pytest", "tests/test_auth_state.py"])
    if auth_check.returncode != 0:
        print("state.json невалиден. Сначала запусти: python auth/save_auth.py")
        return 1

    Path("reports").mkdir(parents=True, exist_ok=True)

    if Path("allure-results").exists():
        shutil.rmtree("allure-results")

    tests_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "--alluredir=allure-results",
            "--junitxml=reports/junit.xml",
        ]
    )

    if tests_run.returncode == 1:
        print("Найдены failed тесты. Генерирую черновики баг-репортов...")
        subprocess.run([sys.executable, "generate_bug_reports.py"])
    else:
        print("Все тесты прошли успешно. Баг-репорты не создаются.")

    return tests_run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
