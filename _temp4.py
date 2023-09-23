import requests
import time

for proxy in [
    # "http://mqxYobQrUK:jVebv7DgsG@176.9.154.71:20016",
    # "http://zGbiyCKZrL:TBs5MVpNMj@176.9.154.71:20020",
    # "http://c3l45hA3En:7QMDxa0to7@176.9.154.71:20029",
    # "http://vyuXyARmsV:VQP0V2MB1f@176.9.154.76:19029",
    # "http://D1Vs0hreh2:Cdq6AV8eOR@176.9.154.76:19035",
    # "http://ZaQtO8Q9Zz:Hb8PzdssCO@176.9.154.71:20037",

    # "http://syN3MA:PaA5ESseTeHy@mproxy.site:10885",
    # "http://azYbgu:yTNae5pYPUDA@mproxy.site:11556",

    "socks5://eppaud:YPEZ3AS2ByF8@kproxy.site:11165"

    ]:

    while True:
        try:
            # req = requests.get("https://httpbin.org/ip", proxies={"http":proxy,"https":proxy}, timeout=15).json()
            req = requests.get("https://i.instagram.com/", proxies={"http":proxy,"https":proxy}, timeout=15)
            break
        except Exception as _:
            time.sleep(5)
            continue

    # print(req["origin"])
    print(req.status_code)
