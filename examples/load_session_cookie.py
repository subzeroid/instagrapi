"""

Script to test loading a browser cookie for instagrapi
and verify session

"""
import sys
from instagrapi import Client

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

def main():
    """Main test function"""
    # Default to LibreWolf if no arguments
    browser_name = sys.argv[1] if len(sys.argv) > 1 else "librewolf"

    print("Browser Cookie Login Test for instagrapi")
    print("=" * 50)
    print(f"Testing browser: {browser_name}")

    success = test_browser_cookie_login(browser_name)

    if success:
        print(f"\n{browser_name} cookie authentication works!")
        print("You can integrate this into your scripts.\n")
        return 0
    else:
        print(f"\n{browser_name} cookie authentication failed.")
        print(f"Check {browser_name} login status or try a different browser.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
