"""Prompt locally for data API keys and save them in Windows Credential Manager.

Keys are entered only at hidden prompts. No file/environment import, network
request, provider activation, plan purchase or model API billing occurs.
"""
from __future__ import annotations

import argparse
import getpass
import sys
import warnings

from backend.app.data_credentials import DataCredentialError, DataCredentialStore, PROVIDERS


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default includes rejected argument values, possibly keys.
        self.exit(2, "Invalid arguments. Run --help. Keys belong only in hidden prompts.\n")


def hidden_key(prompt):
    # Refuse getpass's echoed-input fallback, even if terminal detection passed.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt)


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument("--provider", choices=tuple(PROVIDERS), action="append", help="Configure selected providers; default: all. Can be repeated.")
    parser.add_argument("--status", action="store_true", help="Print configured/missing status only; never print a key or plan label.")
    args = parser.parse_args(argv)
    selected = tuple(dict.fromkeys(args.provider or PROVIDERS))
    if not args.status and not all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr)):
        print("Run setup yourself in an interactive native Windows PowerShell. Do not pipe or redirect keys.")
        return 2
    try:
        store = DataCredentialStore()
        if args.status:
            for provider in selected:
                print(f"{provider}: {'configured' if store.configured(provider) else 'missing'}")
            print("Configured means stored locally, not verified source access or usage permission.")
            return 0
        print("Paste key values only; input is hidden. Enter skips a provider and preserves any saved key.")
        print("Keys stay in Windows Credential Manager. No API calls or billing changes will be made.")
        for provider in selected:
            state = "configured" if store.configured(provider) else "missing"
            print(f"{provider} ({PROVIDERS[provider]}): {state}")
            api_key = hidden_key("API key (hidden; Enter to skip): ")
            if not api_key:
                continue
            # Keep both inputs hidden so an accidental key in the label is not echoed.
            plan = hidden_key("Plan name (hidden; e.g. free, Starter, paid; Enter = unknown): ") or "unknown"
            store.save(provider, api_key, plan)
            api_key = plan = None
            print(f"{provider}: saved and read back successfully.")
        print("Setup finished. Source adapters and their permissions still require separate qualification.")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("Setup stopped. Keys saved in earlier steps remain in Windows Credential Manager.")
        return 2
    except DataCredentialError as exc:
        print(str(exc))
        return 2
    except Exception:
        print("Setup failed without displaying diagnostics. Earlier keys may have been saved. Check the Windows credential store.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
