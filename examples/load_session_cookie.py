"""

Script to load/save browser cookies for instagrapi sessions
with persistence between runs

Usage:
  python load_session_cookie.py               # Use default Chrome
  python load_session_cookie.py firefox       # Use Firefox
  python load_session_cookie.py librewolf     # Use LibreWolf

First run loads from browser and saves session.
Subsequent runs use saved session, fallback to browser if expired.

"""

import os
import sys

from instagrapi import Client

COOKIE_SESSION_FILE = "cookie_session.json"


def get_instagram_cookies_from_browser(browser_name):
    """Get Instagram cookies from specified browser"""
    try:
        import browser_cookie3
    except ImportError:
        print(
            "browser_cookie3 not installed. Install with: pip install browser_cookie3"
        )
        return None

    supported_browsers = {
        "brave": browser_cookie3.brave,
        "chrome": browser_cookie3.chrome,
        "chromium": browser_cookie3.chromium,
        "edge": browser_cookie3.edge,
        "firefox": browser_cookie3.firefox,
        "librewolf": browser_cookie3.librewolf,
        "opera": browser_cookie3.opera,
        "opera_gx": browser_cookie3.opera_gx,
        "safari": browser_cookie3.safari,
        "vivaldi": browser_cookie3.vivaldi,
    }

    if browser_name not in supported_browsers:
        print(f"Unsupported browser: {browser_name}")
        print(f"Supported browsers: {', '.join(supported_browsers.keys())}")
        return None

    try:
        print(f"Loading cookies from {browser_name}...")
        browser_cookies = list(supported_browsers[browser_name]())

        instagram_cookies = {}
        for cookie in browser_cookies:
            if "instagram.com" in cookie.domain:
                instagram_cookies[cookie.name] = cookie.value

        print(f"Found {len(instagram_cookies)} Instagram cookies in {browser_name}")
        return instagram_cookies

    except Exception as e:
        print(f"Failed to load cookies from {browser_name}: {e}")
        return None


def load_saved_session():
    """Try to load and validate a previously saved session"""
    if not os.path.exists(COOKIE_SESSION_FILE):
        return None

    try:
        print("Trying saved cookie session...")
        cl = Client()
        cl.load_settings(COOKIE_SESSION_FILE)

        user_info = cl.account_info()
        print(f"Saved session works for @{user_info.username}")
        return cl

    except Exception as e:
        print(f"Saved session expired: {e}")
        try:
            os.remove(COOKIE_SESSION_FILE)
            print("Removed expired session file")
        except OSError:
            pass
        return None


def authenticate_with_browser_cookies(browser_name):
    """Authenticate using browser cookies, save session if successful"""
    instagram_cookies = get_instagram_cookies_from_browser(browser_name)
    if not instagram_cookies:
        return None

    cl = Client()

    for cookie_name, cookie_value in instagram_cookies.items():
        cl.private.cookies.set(cookie_name, cookie_value, domain="instagram.com")

    print(f"Testing login with {browser_name} browser cookies...")

    try:
        user_info = cl.account_info()
        print(f"Browser cookie login successful: @{user_info.username}")

        print("Saving session for future use...")
        cl.dump_settings(COOKIE_SESSION_FILE)
        print(f"Session saved to {COOKIE_SESSION_FILE}")

        return cl

    except Exception as e:
        print(f"Browser cookie login failed: {e}")
        print("Cookies may be expired or browser session invalid.")
        return None


def main():
    """Main authentication function"""
    browser_name = sys.argv[1] if len(sys.argv) > 1 else "chrome"

    print("Instagram Cookie Authentication for instagrapi")
    print("=" * 55)
    print(f"Target browser: {browser_name}")
    print()

    # Step 1: Try saved session first
    client = load_saved_session()

    if client:
        print("\nAuthentication successful using saved session!")
        return client

    # Step 2: Try browser cookies
    print("\nNo valid saved session found.")
    print(f"Loading fresh cookies from {browser_name}...")

    client = authenticate_with_browser_cookies(browser_name)

    if client:
        print("\nAuthentication successful!")
        print("Session saved for future use.\n")
        return client

    print("\nAuthentication failed.")
    print(f"Please ensure you're logged into Instagram in {browser_name},")
    print("cookies are valid, and browser_cookie3 is installed.\n")
    return None


if __name__ == "__main__":
    result = main()
    if result is None:
        sys.exit(1)
