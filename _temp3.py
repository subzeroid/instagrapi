import re
import json
import time

from instagrapi import Client

def get_aim_parse(account: str):

    RE_AIM = r"(?P<login>.*?):(?P<passw>.*?)\|(?P<user_agent>.*?)\|(?P<android_device_id>.*?)\;(?P<phone_id>.*?)\;(?P<uuid>.*?)\;(?P<advertising_id>.*?)\|.*?mid\=(?P<mid>.*?)\;.*?ds_user_id\=(?P<ds_user_id>.*?)\;.*sessionid\=(?P<sessionid>.*?)\;"
    
    REGEXP_DEVICE = r'Instagram\s(.*?)\sAndroid\s\((\d+)\/(.*?);\s(.*?);\s(.*?);\s(.*?);\s(.*?);\s(.*?);\s(.*?);\s(.*?);\s(.*?)\)'

    USER_AGENT_BASE = (
        "Instagram {app_version} "
        "Android ({android_version}/{android_release}; "
        "{dpi}; {resolution}; {manufacturer}; "
        "{model}; {device}; {cpu}; {locale}; {version_code})"
    )

    aim = re.search(RE_AIM, account)

    device_settings = re.findall(REGEXP_DEVICE, aim.group("user_agent"))

    login = aim.group("login")
    passw =  aim.group("passw")

    device = {
        "login": login,
        "passw": passw,
        "uuids": {
            "phone_id": aim.group("phone_id"),
            "uuid": aim.group("uuid"),
            "advertising_id": aim.group("advertising_id"),
            "android_device_id": aim.group("android_device_id"),
        },
        "mid": aim.group("mid"),
        # "ig_u_rur": aim.group("ig_u_rur"),
        # "ig_www_claim": aim.group("ig_www_claim"),
        # "ig_u_rur": None,
        # "ig_www_claim": None,
        "authorization_data": {
            "ds_user_id": aim.group("ds_user_id"),
            "sessionid": aim.group("sessionid"),
        },
        "cookies": {
            "sessionid": aim.group("sessionid"),
        },
        "last_login": time.time(),

        "device_settings": {
            "app_version": device_settings[0][0],
            "android_version": device_settings[0][1],
            "android_release": device_settings[0][2],
            "dpi": device_settings[0][3],
            "resolution": device_settings[0][4],
            "manufacturer": device_settings[0][5],
            "device": device_settings[0][6],
            "model": device_settings[0][7],
            "cpu": device_settings[0][8],
            "locale": device_settings[0][9],
            "version_code": device_settings[0][10],
        },
        "user_agent": aim.group("user_agent"),
        "username": login,

    }

    return device



import hashlib

REGEXP_DEVICE = r'Instagram\s(.*?)\sAndroid\s\((\d+)\/(.*?)\;\s(.*?)\;\s(.*?)\;\s(.*?)\/(.*?)\;\s(.*?)\;\s(.*?)\;\s(.*?)\;\s(.*?)\)'

user_agent = "Instagram 226.0.0.16.117 Android (24/7.0; 320dpi; 720x1184; unknown/Android; vbox86p; vbox86; en_US; 356747126)"


device_settings = re.findall(REGEXP_DEVICE, user_agent)

dd = {
    "app_version": device_settings[0][0],
    "android_version": device_settings[0][1],
    "android_release": device_settings[0][2],
    "dpi": device_settings[0][3],
    "resolution": device_settings[0][4],
    "manufacturer": device_settings[0][5],
    "device": device_settings[0][6],
    "model": device_settings[0][7],
    "cpu": device_settings[0][8],
    "locale": device_settings[0][9],
    "version_code": device_settings[0][10],
},

bloks_versioning_id = hashlib.sha256(
            json.dumps(dd).encode()
        ).hexdigest()

print("74127b75369d49cc521218cd0a1bb32050ad33839d18cexxxxxxe9e414f68a79")
print(bloks_versioning_id)        