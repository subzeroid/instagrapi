import json
import time
import instagrapi
from instagrapi.utils import dumps
from instagrapi.mixins.challenge import ChallengeChoice
from instadevice.device import Device


def get_new_phone():
    while True:
        new_phone = input(f"Enter new phone: ").strip()
        if new_phone:
            return new_phone
    return None

def get_code_from_sms(username):
    while True:
        code = input(f"Enter code (6 digits) for {username}: ").strip()
        if code and code.isdigit():
            return code
    return None

def challenge_code_handler(username, choice):
    if choice == "change_phone":
        return get_new_phone()
    if choice == ChallengeChoice.SMS:
        return get_code_from_sms(username)
    return False


try:

    proxy = "http://14x12:8T6xsA2m@46.8.31.218:42302"

    device = Device()
    rand_device = device.get_random()

    api = instagrapi.Client(proxy=proxy, timeout=15)
    api.set_settings(rand_device)
    api.challenge_code_handler = challenge_code_handler


    api.login("estiennebasurto", "KgSYbTB4")

    api.get_timeline_feed()


except instagrapi.exceptions.ChallengeUnknownStep as e:
    # восстановливаем аккаунт

    if api.last_json.get("step_name") == "submit_phone":
        wait_seconds = 5

        # вначале отправляет номер
        for attempt in range(24):
            new_phone = api.challenge_code_handler(api.username, "change_phone")
            if new_phone:
                break
            time.sleep(wait_seconds)

        # new_phone = "+6285864439295"

        for _ in range(10):
            try:
                # api._send_private_request("/challenge/", {"phone_number": new_phone})

                resp = api.private.post(
                    f"https://i.instagram.com/api/v1/challenge/",
                    data={
                        "phone_number": new_phone,
                        "challenge_context": api.last_json["challenge_context"],
                    },
                )

                api.last_json = resp.json()

                if api.last_json["status"] == "ok":
                    break

                # {
                #   "step_name": "submit_phone",
                #   "step_data": {
                #     "phone_number": "+6285864439295"
                #   },
                #   "flow_render_type": 3,
                #   "bloks_action": "com.instagram.challenge.navigation.take_challenge",
                #   "cni": 17850586637829908,
                #   "challenge_context": "{\"step_name\": \"submit_phone\", \"cni\": 17850586637829907, \"is_stateless\": false, \"challenge_type_enum\": \"SMS\", \"present_as_modal\": false}",
                #   "challenge_type_enum_str": "SMS",
                #   "status": "ok"
                # }

                # data = {
                #     "bk_client_context": dumps({"bloks_version": api.bloks_versioning_id, "styles_id": "instagram"}),
                #     "challenge_context": api.last_json.get("challenge_context"),
                #     "bloks_versioning_id": api.bloks_versioning_id,
                #     "phone_number": new_phone
                # }
                # api.bloks_action(api.last_json.get("bloks_action"), data)

            except Exception as e:
                time.sleep(2)
                continue


        # api.inject_sessionid_to_public()

        # for _ in range(10):
        #     try:
        #         # api._send_public_request(api.PUBLIC_API_URL + "challenge/", {
        #         #     "phone_number": new_phone,
        #         #     "challenge_context": "{\"step_name\":+\"\",+\"is_stateless\":+false,+\"present_as_modal\":+false}",
        #         #     "next": "/accounts/onetap/%3Fnext%3D%252F"
        #         # })
        #         # api._send_private_request("/challenge/", {"phone_number": new_phone})
        #         api._send_private_request("/challenge/", {
        #             "phone_number": new_phone,
        #             "challenge_context": "{\"step_name\":+\"\",+\"is_stateless\":+false,+\"present_as_modal\":+false}",
        #             "next": "/accounts/onetap/%3Fnext%3D%252F"
        #         })
        #     except Exception as e:
        #         time.sleep(2)
        #         continue

        # потом отправляем код
        for attempt in range(24):
            code = api.challenge_code_handler(api.username, ChallengeChoice.SMS)
            if code:
                break
            time.sleep(wait_seconds)
        for _ in range(10):
            try:

                resp = api.private.post(
                    f"https://i.instagram.com/api/v1/challenge/",
                    data={
                        "security_code": code,
                        "challenge_context": api.last_json["challenge_context"],
                    },
                )

                api.last_json = resp.json()

                if api.last_json["status"] == "ok":
                    break

                # api._send_private_request("/challenge/", {"security_code": code})
            except Exception as e:
                time.sleep(2)
                continue

        # assert 'logged_in_user' in client.last_json
        assert api.last_json.get("action", "") == "close"
        assert api.last_json.get("status", "") == "ok"


    time.sleep(1)
