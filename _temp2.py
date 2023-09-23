from instagrapi import Client
import time
import user_agent
from instadevice.device import Device

PROXIES = [
    # 'http://syN3MA:PaA5ESseTeHy@nproxy.site:10885', # mobileproxy.space
    # 'http://14x12:8T6xsA2m@46.8.31.218:42102', # proxy-seller.com
    'http://c3l45hA3En:7QMDxa0to7@176.9.154.71:20029' # bot
]

ACCS = """
williamphillips8739:qMDFkI2mkL
"""

accs = ACCS.strip()
print("\n")
for proxy in PROXIES:
    time.sleep(1)

    cl = Client(timeout=10, proxy=proxy)

    print(f"⭐️ Прокси: {proxy}\n")

    for acc in accs.split('\n'):
        time.sleep(1)

        print("🟣 Проверка акка: "+acc.split(':')[0])
        for _ in range(4):
            device = Device()
            rand_device = device.get_random()
            rand_device.update({
                'web_user_agent': user_agent.generate_user_agent()
            })
            try:
                cl.set_settings(rand_device)
                # cl.set_timezone_offset(21600)  # Нур-Султан
                # cl.set_locale("ru_KZ")
                # cl.set_country("KZ")
                # cl.set_country_code(7)
                cl.login(acc.split(':')[0], acc.split(':')[1])
                cl.get_timeline_feed()
                sett = cl.get_settings()
                print(sett)
                print("✅ Есть логин!")
                break
            except Exception as e:
                time.sleep(3)
                print(f"❌ ОШИБКА: {e}")

    print("\n")