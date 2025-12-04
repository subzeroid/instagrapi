"""

Script to load/save browser cookies for instagrapi sessions
with persistence between runs

Usage:
  python load_session_cookie.py               # Use default LibreWolf
  python load_session_cookie.py chrome        # Use Chrome
  python load_session_cookie.py firefox       # Use Firefox

First run loads from browser and saves session.
Subsequent runs use saved session, fallback to browser if expired.

$ python load_session_cookie.py
Instagram Cookie Authentication for instagrapi
=======================================================
Target browser: librewolf


No valid saved session found.
Loading fresh cookies from librewolf...
Loading cookies from librewolf...
Found X Instagram cookies in librewolf
Testing login with librewolf browser cookies...
Browser cookie login successful: @username
Saving session for future use...
Session saved to cookie_session.json

Authentication successful!
Session saved for future use.

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
        print("browser_cookie3 not installed. Install with: pip install browser_cookie3")
        return None

    # Map browser names to browser_cookie3 functions
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

        # Get raw browser cookies
        browser_cookies = list(supported_browsers[browser_name]())

        # Filter for Instagram cookies
        instagram_cookies = {}
        for cookie in browser_cookies:
            if 'instagram.com' in cookie.domain:
                instagram_cookies[cookie.name] = cookie.value

        print(f"Found {len(instagram_cookies)} Instagram cookies in {browser_name}")
        return instagram_cookies

    except Exception as e:
        print(f"Failed to load cookies from {browser_name}: {e}")
        return None

def test_browser_cookie_login(browser_name):
    """Test loading Instagram cookies from specified browser"""

    # Get cookies from browser
    instagram_cookies = get_instagram_cookies_from_browser(browser_name)
    if not instagram_cookies:
        print(f"No Instagram cookies found in {browser_name}. Log into Instagram in {browser_name} first.")
        return False

    if not instagram_cookies:
        print(f"No Instagram cookies found in {browser_name}.")
        return False

    # Create instagrapi client and load cookies
    cl = Client()

    # Load cookies into instagrapi session
    for cookie_name, cookie_value in instagram_cookies.items():
        cl.private.cookies.set(cookie_name, cookie_value, domain='instagram.com')

    print(f"Testing login with {browser_name} browser cookies...")

    # Try to access user info to test login
    try:
        user_info = cl.account_info()
        print(f"Success! Logged in as @{user_info.username}")
        print(f"User ID: {user_info.pk}")
        return True

    except Exception as login_error:
        print(f"Cookie login failed: {login_error}")
        print("Cookies may be expired or browser session invalid.")
        return False

def test_saved_cookie_session():
    """Test if saved cookie session still works"""
    if not os.path.exists(COOKIE_SESSION_FILE):
        return None  # No saved session

    try:
        print("Trying saved cookie session...")
        cl = Client()

        # Load saved session
        session = cl.load_settings(COOKIE_SESSION_FILE)
        cl.set_settings(session)

        # Test by trying to get account info
        user_info = cl.account_info()
        print(f"Saved session works for @{user_info.username}")
        return cl

    except Exception as e:
        print(f"Saved session expired: {e}")
        # Remove expired session file
        try:
            os.remove(COOKIE_SESSION_FILE)
            print("Removed expired session file")
        except:
            pass
        return None

def authenticate_with_browser_cookies(browser_name):
    """Authenticate using browser cookies, save session if successful"""

    # Get cookies from browser
    instagram_cookies = get_instagram_cookies_from_browser(browser_name)
    if not instagram_cookies:
        return None

    # Create instagrapi client and load cookies
    cl = Client()

    # Load cookies into instagrapi session
    for cookie_name, cookie_value in instagram_cookies.items():
        cl.private.cookies.set(cookie_name, cookie_value, domain='instagram.com')

    print(f"Testing login with {browser_name} browser cookies...")

    # Try to access user info to test login
    try:
        user_info = cl.account_info()
        print(f"Browser cookie login successful: @{user_info.username}")

        # Save successful session for next time
        print("Saving session for future use...")
        cl.dump_settings(COOKIE_SESSION_FILE)
        print(f"Session saved to {COOKIE_SESSION_FILE}")

        return cl

    except Exception as login_error:
        print(f"Browser cookie login failed: {login_error}")
        print("Cookies may be expired or browser session invalid.")
        return None

def main():
    """Main authentication function"""
    # Default to LibreWolf if no arguments
    browser_name = sys.argv[1] if len(sys.argv) > 1 else "librewolf"

    print("Instagram Cookie Authentication for instagrapi")
    print("=" * 55)
    print(f"Target browser: {browser_name}")
    print()

    # Step 1: Try saved cookie session first
    client = test_saved_cookie_session()

    if client:
        print("\nAuthentication successful using saved session!")
        print("No need to load fresh cookies.\n")
        return client

    print("\nNo valid saved session found.")
    print(f"Loading fresh cookies from {browser_name}...")

    # Step 2: Try browser cookies if saved session failed
    client = authenticate_with_browser_cookies(browser_name)

    if client:
        print("\nAuthentication successful!")
        print("Session saved for future use.\n")
        return client
    else:
        print("\nAuthentication failed.")
        print(f"Please ensure you're logged into Instagram in {browser_name},")
        print("cookies are valid, and browser_cookie3 is installed.\n")
        return None

if __name__ == "__main__":
    # Just run the authentication (don't exit on failure for integration)
    result = main()
    if result is None:
        sys.exit(1)
