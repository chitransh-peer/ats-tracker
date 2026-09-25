"""Test SMTP credentials directly, without deploying anything.

Debugging mail through a deploy is a three-minute round trip per attempt, and
it cannot tell you whether the credentials are wrong or simply never reached
the service. This talks to the mail server from wherever you run it and reports
exactly what the server said.

Usage:
    python -m scripts.check_smtp

It prompts for everything and echoes nothing secret. Nothing is stored, and no
message is sent unless you give it a recipient.
"""

import getpass
import smtplib
import sys
from email.message import EmailMessage


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or default


def run() -> int:
    print("SMTP credential check\n")

    host = _ask("SMTP host", "smtp-relay.brevo.com")
    port = int(_ask("Port", "587"))
    # Both are required. Submitting an empty one produces exactly the same
    # "authentication failed" the real credentials would on a bad password,
    # which makes the run worse than useless -- it looks like an answer.
    username = ""
    while not username:
        username = _ask("Username (your provider's SMTP login)")
        if not username:
            print("  A username is required. Copy the 'Login' from your provider's SMTP page.")

    password = ""
    while not password:
        password = getpass.getpass("Password / SMTP key (hidden): ").strip()
        if not password:
            print("  A password is required. Nothing is echoed, so type or paste it blind.")

    # A pasted credential very often carries a trailing space or newline, and
    # the resulting failure is indistinguishable from a wrong password.
    if password != password.strip() or username != username.strip():
        print("\nNote: leading or trailing whitespace was trimmed from your input.")

    print(f"\nConnecting to {host}:{port} ...")
    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            print("Connected. Starting TLS ...")
            smtp.starttls()
            smtp.ehlo()
            print(f"Authenticating as {username!r} ...")
            smtp.login(username, password)
            print("\n*** Authentication succeeded. These credentials are correct. ***")

            recipient = _ask("\nSend a test message to (blank to skip)")
            if recipient:
                sender = _ask("From address (must be verified with your provider)")
                message = EmailMessage()
                message["From"] = sender
                message["To"] = recipient
                message["Subject"] = "ATS Tracker SMTP check"
                message.set_content("If you are reading this, SMTP is working.")
                smtp.send_message(message)
                print(f"\nAccepted for delivery to {recipient}. Check the inbox, and spam.")
    except smtplib.SMTPAuthenticationError as exc:
        detail = exc.smtp_error.decode(errors="replace")
        print(f"\n*** Authentication REJECTED: {exc.smtp_code} {detail} ***")
        print(
            "\nThe credentials themselves are being refused, so redeploying will not help.\n"
            "Usual causes:\n"
            "  - the API key was used instead of the SMTP key\n"
            "  - the username is not the provider's SMTP login\n"
            "  - the account is not yet activated for sending"
        )
        return 1
    except smtplib.SMTPSenderRefused as exc:
        print(f"\n*** Sender refused: {exc.smtp_error.decode(errors='replace')} ***")
        print("The login worked. That From address is not verified with your provider.")
        return 1
    except OSError as exc:
        print(f"\n*** Could not reach {host}:{port} — {exc} ***")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run())
