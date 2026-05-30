from __future__ import annotations

import os
import re
import smtplib
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ENV_PATH = Path(".env")


def load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv()

SITE_URL = os.getenv("SICA_URL", "https://restaurante.szn.ifsp.edu.br/sicaweb/home")
PRONTUARIO = os.getenv("SICA_PRONTUARIO", "sz3083179")
DEST_EMAIL = os.getenv("DEST_EMAIL", "dujunarezi@gmail.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
HEADLESS = os.getenv("HEADLESS", "true").lower() != "false"
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "30000"))
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))
ERROR_PATH = ARTIFACTS_DIR / "last_error.txt"
STATUS_PATH = ARTIFACTS_DIR / "status.txt"


@dataclass
class TicketResult:
    token: str | None
    visible_text: str
    screenshot_path: Path
    html_path: Path


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def first_non_empty(values: Iterable[str | None]) -> str | None:
    for value in values:
        if value:
            value = clean_text(value)
            if value:
                return value
    return None


def find_prontuario_input(page):
    candidates = [
        page.get_by_label(re.compile("prontu[aá]rio", re.I)),
        page.locator("input[name*='pront' i]"),
        page.locator("input[id*='pront' i]"),
        page.locator("input[placeholder*='pront' i]"),
        page.locator("form input[type='text']").first,
    ]
    for locator in candidates:
        try:
            if locator.count() > 0:
                return locator.first
        except Exception:
            continue
    raise RuntimeError("Não encontrei o campo de prontuário no site.")


def click_submit(page):
    button_candidates = [
        page.get_by_role("button", name=re.compile("enviar|gerar", re.I)),
        page.locator("input[type='submit']"),
        page.locator("button[type='submit']"),
        page.locator("form button").first,
    ]
    for locator in button_candidates:
        try:
            if locator.count() > 0:
                locator.first.click()
                return
        except Exception:
            continue
    raise RuntimeError("Não encontrei o botão para enviar/gerar o ticket.")


def extract_token(text: str) -> str | None:
    normalized = clean_text(text)
    patterns = [
        r"(?:token|ticket|c[oó]digo|senha)\s*[:#-]?\s*([A-Z0-9-]{4,})",
        r"\b([A-Z]{2,}\d{3,}|\d{5,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, re.I)
        if match:
            return match.group(1)
    return None


def generate_ticket() -> TicketResult:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now_stamp()
    screenshot_path = ARTIFACTS_DIR / f"sica_ticket_{stamp}.png"
    html_path = ARTIFACTS_DIR / f"sica_ticket_{stamp}.html"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        page.set_default_timeout(TIMEOUT_MS)

        try:
            page.goto(SITE_URL, wait_until="domcontentloaded")
            input_locator = find_prontuario_input(page)
            input_locator.fill(PRONTUARIO)

            before_text = clean_text(page.locator("body").inner_text())
            click_submit(page)

            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            page.wait_for_timeout(3000)
            after_text = clean_text(page.locator("body").inner_text())
            page.screenshot(path=str(screenshot_path), full_page=True)
            html_path.write_text(page.content(), encoding="utf-8")
        finally:
            browser.close()

    token = first_non_empty(
        [
            extract_token(after_text),
            extract_token(after_text.replace(before_text, "")),
        ]
    )

    return TicketResult(
        token=token,
        visible_text=after_text,
        screenshot_path=screenshot_path,
        html_path=html_path,
    )


def build_email(result: TicketResult) -> EmailMessage:
    subject_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    if result.token:
        subject = f"SICA token gerado - {subject_date}"
        body = (
            f"Token encontrado para o prontuário {PRONTUARIO}:\n\n"
            f"{result.token}\n\n"
            f"Site: {SITE_URL}\n"
            f"Gerado em: {subject_date}\n"
        )
    else:
        preview = result.visible_text[:1500] if result.visible_text else "Sem texto visível."
        subject = f"SICA ticket gerado (revisar screenshot) - {subject_date}"
        body = (
            f"Não consegui isolar o token automaticamente para o prontuário {PRONTUARIO}.\n\n"
            f"Enviei a screenshot e o HTML para conferência.\n\n"
            f"Prévia do texto visível:\n{preview}\n\n"
            f"Site: {SITE_URL}\n"
            f"Gerado em: {subject_date}\n"
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = EMAIL_FROM
    message["To"] = DEST_EMAIL
    message.set_content(body)

    for attachment_path, mime_type in (
        (result.screenshot_path, "image/png"),
        (result.html_path, "text/html"),
    ):
        maintype, subtype = mime_type.split("/", 1)
        with attachment_path.open("rb") as file:
            message.add_attachment(
                file.read(),
                maintype=maintype,
                subtype=subtype,
                filename=attachment_path.name,
            )

    return message


def send_email(message: EmailMessage) -> None:
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError(
            "Defina SMTP_USER e SMTP_PASS antes de rodar. "
            "No Gmail, use uma senha de app."
        )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(message)


def validate_env() -> None:
    required = {
        "SICA_PRONTUARIO": PRONTUARIO,
        "DEST_EMAIL": DEST_EMAIL,
        "SMTP_USER": SMTP_USER,
        "SMTP_PASS": SMTP_PASS,
        "EMAIL_FROM": EMAIL_FROM,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Secrets/variáveis ausentes: " + ", ".join(missing)
        )


def write_status(message: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(message + "\n", encoding="utf-8")


def main() -> int:
    try:
        validate_env()
        result = generate_ticket()
        message = build_email(result)
        send_email(message)
        write_status("OK: ticket processado e email enviado.")
        print("Ticket processado com sucesso.")
        if result.token:
            print(f"Token encontrado: {result.token}")
        else:
            print("Token não identificado automaticamente; screenshot enviada por email.")
        return 0
    except Exception as exc:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        error_text = "".join(traceback.format_exception(exc))
        ERROR_PATH.write_text(error_text, encoding="utf-8")
        write_status(f"ERRO: {exc}")
        print(f"Erro ao gerar/enviar ticket: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
