import imaplib
import email
import os
import re
import time
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime


def _decode_mime_header(value: str) -> str:
    parts: list[str] = []
    for chunk, encoding in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(encoding or "utf-8", errors="ignore"))
        else:
            parts.append(chunk)
    return "".join(parts)


def _extract_text_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="ignore")
        return ""

    payload = msg.get_payload(decode=True)
    if payload:
        return payload.decode(errors="ignore")
    return ""


_INTERNALDATE_RE = re.compile(r'INTERNALDATE "([^"]+)"')


def _parse_internaldate(fetch_response_meta: bytes) -> datetime | None:
    m = _INTERNALDATE_RE.search(fetch_response_meta.decode(errors="ignore"))
    if not m:
        return None
    try:
        dt = parsedate_to_datetime(m.group(1))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extract_fetch_meta_bytes(msg_data) -> bytes:
    """
    imaplib возвращает список, где:
    - tuple[0] содержит метаданные FETCH (в т.ч. INTERNALDATE),
    - tuple[1] содержит тело (RFC822).
    INTERNALDATE может оказаться и в отдельных bytes-элементах списка.
    """
    parts: list[bytes] = []
    for item in msg_data:
        if isinstance(item, tuple) and item and isinstance(item[0], (bytes, bytearray)):
            parts.append(bytes(item[0]))
        elif isinstance(item, (bytes, bytearray)):
            parts.append(bytes(item))
    return b" ".join(parts)


def get_latest_otp_code(
    email_user: str,
    app_password: str,
    mailbox: str = "INBOX",
    sender_filter: str | None = None,
    subject_filter: str | None = None,
    timeout_seconds: int = 60,
    poll_interval: int = 5,
) -> str:
    wait_started_at = datetime.now(timezone.utc)
    cutoff = wait_started_at - timedelta(seconds=30)
    end_time = time.time() + timeout_seconds

    while time.time() < end_time:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, app_password)
        mail.select(mailbox)

        # IMAP SEARCH используем только ASCII-критерии.
        # Берём список UID писем от ads@ktsf.ru и дальше фильтруем локально по Subject.
        status, data = mail.uid(
            "search",
            None,
            '(FROM "ads@ktsf.ru")',
        )
        if status != "OK":
            mail.logout()
            time.sleep(poll_interval)
            continue

        uids = data[0].split()
        if not uids:
            mail.logout()
            time.sleep(poll_interval)
            continue

        debug = os.getenv("OTP_DEBUG") == "1"
        otp_re = re.compile(r"Ваш код для подтверждения\s+(\d{5})")

        if debug:
            # Диагностика: покажем последние 5 писем от ads@ktsf.ru.
            for uid in list(reversed(uids))[:5]:
                status, msg_data = mail.uid("fetch", uid, "(INTERNALDATE RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue

                meta_bytes = _extract_fetch_meta_bytes(msg_data)
                internaldate = _parse_internaldate(meta_bytes)

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                from_value = _decode_mime_header(msg.get("From", "") or "")
                subject = _decode_mime_header(msg.get("Subject", "") or "")
                body = _extract_text_body(msg)

                preview = (f"{subject}\n{body}")[:300].replace("\r", "\\r").replace("\n", "\\n")
                m = otp_re.search(f"{subject}\n{body}")
                found_code = m.group(1) if m else None

                print(
                    "[otp_helper][debug] "
                    f"uid={uid.decode(errors='ignore')} "
                    f"internaldate={internaldate.isoformat() if internaldate else None} "
                    f"from={from_value!r} "
                    f"subject={subject!r} "
                    f"preview={preview!r} "
                    f"otp={found_code!r}"
                )

        best_uid: bytes | None = None
        best_internaldate: datetime | None = None
        best_code: str | None = None

        # Проходим письма от самых свежих UID к более старым, но выбираем по INTERNALDATE.
        for uid in reversed(uids):
            status, msg_data = mail.uid("fetch", uid, "(INTERNALDATE RFC822)")
            if status != "OK" or not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple):
                continue

            meta_bytes = _extract_fetch_meta_bytes(msg_data)
            internaldate = _parse_internaldate(meta_bytes)
            if internaldate is None:
                continue
            if internaldate < cutoff:
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = _decode_mime_header(msg.get("Subject", "") or "")
            body = _extract_text_body(msg)
            text_to_search = f"{subject}\n{body}"

            match = otp_re.search(text_to_search)
            if not match:
                if debug:
                    print(
                        "[otp_helper][debug] "
                        f"skip uid={uid.decode(errors='ignore')} "
                        f"internaldate={internaldate.isoformat()} otp=None"
                    )
                continue

            code = match.group(1)
            if debug:
                print(
                    "[otp_helper][debug] "
                    f"candidate uid={uid.decode(errors='ignore')} "
                    f"internaldate={internaldate.isoformat()} otp={code}"
                )

            if best_internaldate is None or internaldate > best_internaldate:
                best_uid = uid
                best_internaldate = internaldate
                best_code = code

        if best_code is not None:
            if debug:
                print(
                    "[otp_helper][debug] "
                    f"selected uid={best_uid.decode(errors='ignore') if best_uid else None} "
                    f"internaldate={best_internaldate.isoformat() if best_internaldate else None} "
                    f"otp={best_code}"
                )
            mail.logout()
            return best_code

        mail.logout()
        time.sleep(poll_interval)

    raise TimeoutError("Не удалось получить OTP-код из почты вовремя.")