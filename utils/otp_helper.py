import imaplib
import email
import os
import re
import time
from email.header import decode_header


def get_latest_otp_code(
    email_user: str,
    app_password: str,
    mailbox: str = "INBOX",
    sender_filter: str | None = None,
    subject_filter: str | None = None,
    timeout_seconds: int = 60,
    poll_interval: int = 5,
) -> str:
    end_time = time.time() + timeout_seconds

    while time.time() < end_time:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, app_password)
        mail.select(mailbox)

        status, messages = mail.search(None, "ALL")
        if status != "OK":
            mail.logout()
            time.sleep(poll_interval)
            continue

        message_ids = messages[0].split()
        message_ids = list(reversed(message_ids))

        for msg_id in message_ids[:10]:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject, encoding = decode_header(msg.get("Subject", ""))[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="ignore")

            from_value = msg.get("From", "")

            if sender_filter and sender_filter.lower() not in from_value.lower():
                continue

            if subject_filter and subject_filter.lower() not in subject.lower():
                continue

            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors="ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")

            text_to_search = f"{subject}\n{body}"

            matches = re.findall(r"\b(\d{4,8})\b", text_to_search)
            if matches:
                mail.logout()
                return matches[-1]

        mail.logout()
        time.sleep(poll_interval)

    raise TimeoutError("Не удалось получить OTP-код из почты вовремя.")