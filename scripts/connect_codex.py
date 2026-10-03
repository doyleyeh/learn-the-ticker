"""User-interactive, no-inference sign-in for the dedicated desktop connection.

Device codes appear only in an interactive terminal, never a report or redirected
log. Codex stores durable authentication in the OS credential store.
"""
import argparse
import asyncio
import sys
import webbrowser

from backend.app.codex_login import CodexLogin, DEVICE_URL
from backend.app.codex_runtime import CodexRuntime
from backend.app.runtime_base import AIRuntime
from scripts.qualify_codex import resolve_profile


async def connect(profile):
    version = await AIRuntime.check(CodexRuntime(profile))
    if not version.installed or version.qualification == "unqualified":
        print("The installed Codex version is unsupported. No sign-in was started.")
        return 2
    login = CodexLogin(profile)
    try:
        state = await login.start()
        if state.status == "pending":
            print("Authorize only this Learn the Ticker request on the official ChatGPT page.")
            print("Device code:", state.user_code)
            print("Sign-in page:", DEVICE_URL)
            print("This requests no inference. Press Ctrl+C to cancel.")
            webbrowser.open(DEVICE_URL)
            await login.task
        state = login.snapshot()
        print(state.message)
        return 0 if state.status == "authenticated" else 2
    finally:
        await login.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="Dedicated app-owned profile, never the main developer profile")
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Run sign-in yourself in an interactive terminal. Device codes must not be redirected to logs.")
        return 2
    try:
        profile = resolve_profile(args.profile)
        return asyncio.run(connect(profile))
    except KeyboardInterrupt:
        print("Sign-in cancelled. No inference was requested.")
        return 2
    except Exception:
        print("Sign-in failed. Check the installed runtime, isolated profile and OS credential store.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
