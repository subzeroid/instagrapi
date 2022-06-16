from instagrapi import Client

ACCOUNT_USERNAME = 'aksyonov6632'
ACCOUNT_PASSWORD = '7v3moUinw'

SETTINGS = '{"uuids": {"phone_id": "f4c61128-3d2e-4d57-8343-8d81310aeda7", "uuid": "c5208bc4-277b-4a97-ae2a-a30b272fa517", "client_session_id": "8a702f34-e736-4197-a00e-6f668211612a", "advertising_id": "4f9acfbd-300e-45d5-ae8e-c66ca90ce6fb", "android_device_id": "android-3fc6896b2f1a8140", "request_id": "b9803352-68f6-476a-aa50-c3f45b6d6079", "tray_session_id": "e1906013-1316-4108-8537-c0e47ee07aa4"}, "mid": "YXlxegABAAH3EGQgfwPfWwBEkgE7", "authorization_data": {"ds_user_id": "47809562175", "sessionid": "47809562175%3AyIyyKFf6X3F2Iv%3A22", "should_use_header_over_cookies": false}, "cookies": {"csrftoken": "VSBQd9RWXjrTRKxYEqBg4kqwz8DzuiW4", "ds_user_id": "47809562175", "mid": "YXlxegABAAH3EGQgfwPfWwBEkgE7", "rur": "\\"RVA\\\\05447809562175\\\\0541666884866:01f75b0a484eddd9a433e3b88bd4ad755e7199d252d6f4f4ca38b330fdeb65e23551b1e4\\"", "sessionid": "47809562175%3AyIyyKFf6X3F2Iv%3A22"}, "last_login": 1635348866.3718505, "device_settings": {"app_version": "143.0.0.25.121", "android_version": "29", "android_release": "10", "dpi": "280dpi", "resolution": "720x1280", "manufacturer": "samsung", "device": "SM-J400M", "model": "j4lte", "cpu": "samsungexynos7570", "lang": "pt_BR", "version_code": "216817269"}, "user_agent": "Instagram 143.0.0.25.121 Android (29/10; 280dpi; 720x1280; samsung; SM-J400M; j4lte; samsungexynos7570; pt_BR; 216817269)", "web_user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2686.98 Safari/537.36", "username": "", "country": "US", "locale": "en_US", "timezone_offset": -14400}'

# cl = Client(proxy='http://icofreakru:bbdc88b9@5.61.56.223:12143/')
cl = Client(timeout=10)
cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)

# cl.login_by_settings(SETTINGS)

user_id = cl.user_id_from_username("marvel")
medias = cl.user_medias(user_id, 20)
stories = cl.user_stories(user_id)

sett = cl.get_settings()

print(medias)