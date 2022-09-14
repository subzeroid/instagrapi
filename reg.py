import instagrapi
import mimesis
import random
from instadevice.device import Device


if __name__ == "__main__":

    device = Device()
    rand_device = device.get_random()

    api = instagrapi.Client(
        # settings=rand_device,
        timeout=15,
        proxy="http://14x12:8T6xsA2m@46.8.31.218:42102",
    )

    person = mimesis.Person("en")

    username = person.username(
        "".join(random.sample(list("llddl"), len(list("llddl"))))
    )
    email = username + "@hhorse.ru"
    password = person.password()

    user = api.signup(
        username=username,
        password=password,
        email=email,
        phone_number="79202221142",
        full_name=person.full_name(),
        year=1976,
        month=6,
        day=12,
    )

    print(user.username)

    print("OK")
