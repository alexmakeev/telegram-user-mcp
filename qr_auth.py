#!/usr/bin/env python3
"""Telegram QR Code Authentication.

Displays a QR code in the terminal. Scan it with your Telegram app
to authorize this session. Saves the session string to .env file.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv, set_key
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')


def display_qr(url: str) -> None:
    """Display QR code in terminal using segno."""
    import segno
    print("\n" + "=" * 50)
    print("  Scan this QR code with your Telegram app")
    print("  (Settings → Devices → Link Desktop Device)")
    print("=" * 50 + "\n")
    qr = segno.make(url)
    qr.terminal(compact=True)
    print()


async def authenticate() -> str:
    """Run QR authentication flow, return session string."""
    load_dotenv(ENV_PATH, override=True)

    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')

    if not api_id or not api_hash:
        print("ERROR: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
        print(f"  File: {ENV_PATH}")
        print("  Get them at: https://my.telegram.org → API development")
        sys.exit(1)

    client = TelegramClient(StringSession(), int(api_id), api_hash)
    await client.connect()

    try:
        qr_login = await client.qr_login()
        display_qr(qr_login.url)

        print("Waiting for scan...")
        try:
            await qr_login.wait(timeout=300)
        except asyncio.TimeoutError:
            print("\nQR code expired (300s timeout). Run the script again.")
            sys.exit(1)
        except SessionPasswordNeededError:
            password = input("\n2FA enabled. Enter your password: ")
            await client.sign_in(password=password)

        me = await client.get_me()
        session_string = StringSession.save(client.session)

        print(f"\nAuthenticated as: {me.first_name} (@{me.username or 'no username'})")
        print(f"Session string saved to: {ENV_PATH}")

        return session_string

    finally:
        await client.disconnect()


def save_session(session_string: str) -> None:
    """Save session string to .env file."""
    try:
        set_key(ENV_PATH, 'TELEGRAM_SESSION_STRING', session_string)
    except PermissionError:
        print(f"\nCould not write to {ENV_PATH} (permission denied)")
        print(f"Add this to your .env manually:")
        print(f"TELEGRAM_SESSION_STRING={session_string}")


def main():
    session_string = asyncio.run(authenticate())
    print(f"\nSESSION_STRING={session_string}")
    save_session(session_string)
    print("\nDone! You can now start the MCP server.")


if __name__ == '__main__':
    main()
