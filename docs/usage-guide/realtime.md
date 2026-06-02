# Realtime MQTT

!!! warning
    Realtime MQTT support is experimental. Instagram can change this private transport without notice.

The realtime client opens Instagram's MQTToT connection for live events after login.
It is useful when you need callbacks for realtime payloads instead of polling HTTP endpoints.
It can also publish lightweight Direct actions over MQTT. Use the regular Direct methods for media sends
and complete thread management.

FBNS push notifications use a separate `mqtt-mini.facebook.com` device-auth connection. Use FBNS when you need
Instagram push payloads, for example Direct message notification callbacks.

| Method | Return | Description |
| --- | --- | --- |
| `realtime_connect(transport=None)` | `RealtimeClient` | Create and connect the stateful realtime client |
| `realtime_disconnect()` | `None` | Disconnect the active realtime client |
| `realtime_on(event, handler)` | `None` | Register an event handler on the active realtime client |
| `realtime_ping()` | `bool` | Send a keepalive ping and wait for `PINGRESP` |
| `realtime_read_once()` | `Any` | Read one packet from the active realtime client |
| `fbns_connect(transport=None, auth=None, register=True)` | `FbnsClient` | Create, connect, and register the stateful FBNS client |
| `fbns_disconnect()` | `None` | Disconnect the active FBNS client |
| `fbns_on(event, handler)` | `None` | Register an event handler on the active FBNS client |
| `fbns_ping()` | `bool` | Send an FBNS keepalive ping and wait for `PINGRESP` |
| `fbns_read_once()` | `Any` | Read one packet from the active FBNS client |

`RealtimeClient` also exposes lower-level helpers:

| Method | Description |
| --- | --- |
| `on(event, handler)` | Register a handler for `receive`, `message`, or `realtime_sub` |
| `graph_ql_subscribe(subscriptions)` | Publish raw GraphQL realtime subscriptions |
| `skywalker_subscribe(subscriptions)` | Publish raw Skywalker subscriptions |
| `iris_subscribe(seq_id, snapshot_at_ms)` | Publish Direct inbox sync state for message-sync events |
| `direct_subscribe(amount=1)` | Fetch Direct inbox sync state and subscribe to message-sync events |
| `direct_send_text(thread_id, text, client_context=None)` | Publish a Direct text message over MQTT |
| `direct_send_reaction(thread_id, item_id, emoji="", ...)` | Publish a Direct reaction over MQTT |
| `direct_mark_seen(thread_id, item_id)` | Publish Direct seen state over MQTT |
| `direct_indicate_activity(thread_id, is_active=True, client_context=None)` | Publish Direct typing/activity state over MQTT |
| `send_foreground_state(...)` | Publish foreground state and optional topic changes |
| `publish_json(topic, data)` | Publish a JSON payload to a raw MQTToT topic |
| `ping()` | Send a keepalive ping and wait for `PINGRESP` |
| `read_once()` | Read and dispatch one packet |

Basic receive loop:

``` python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)


def handle_receive(event):
    print(event["topic"], event["payload"])


cl.realtime_on("receive", handle_receive)
rt = cl.realtime_connect()

while True:
    cl.realtime_read_once()
```

Receive Direct message sync payloads:

``` python
import json

from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)


def handle_direct_message(payload):
    print(json.dumps(payload, indent=2, ensure_ascii=False))


cl.realtime_on("message", handle_direct_message)

rt = cl.realtime_connect()
rt.direct_subscribe()

try:
    # Optional keepalive check for smoke tests or long-running workers.
    rt.ping()

    while True:
        cl.realtime_read_once()
except KeyboardInterrupt:
    pass
finally:
    cl.realtime_disconnect()
```

Send lightweight Direct actions over MQTT:

``` python
rt.direct_send_text(thread_id, "Hello from MQTT")
rt.direct_send_reaction(thread_id, item_id, emoji="❤️")
rt.direct_indicate_activity(thread_id, is_active=True)
rt.direct_mark_seen(thread_id, item_id)
```

For photos, videos, voice, thread creation, request approval, and other full Direct operations, use the normal
`direct_*` HTTP methods. The MQTT payload shape is private and can change server-side, so inspect received
dictionaries before depending on nested keys.

Receive FBNS push notifications:

``` python
import json

from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)


def handle_push(payload):
    print(json.dumps(payload, indent=2, ensure_ascii=False))


cl.fbns_on("push", handle_push)
fbns = cl.fbns_connect()

try:
    fbns.ping()
    while True:
        cl.fbns_read_once()
except KeyboardInterrupt:
    pass
finally:
    cl.fbns_disconnect()
```

`fbns_connect()` registers the FBNS token with Instagram's private push register endpoint. The device-auth state
returned by the broker is stored in `settings["fbns_auth"]`, so `dump_settings()` can persist it with the normal
session data.

Subscribe to raw realtime topics:

``` python
rt.graph_ql_subscribe(["<graphql-subscription>"])
rt.skywalker_subscribe(["<skywalker-subscription>"])
```

Raw GraphQL and Skywalker subscription strings are advanced and unstable. Message sync is subscribed by the default
connection topics, so the Direct message example above does not need an extra raw subscription.

Events:

* `receive` is emitted for every decoded publish packet as `{"topic": topic, "payload": payload}`.
* `message` is emitted for message-sync payloads.
* `direct` is emitted for parsed Direct realtime payloads from message-sync or realtime-sub streams.
* `typing`, `seen`, and `presence` are emitted for Direct realtime payloads that can be classified.
* `send_response` is emitted for MQTT Direct command responses.
* `iris_sub_response` is emitted for Iris subscription responses.
* `realtime_sub` is emitted for realtime subscription payloads.
* `push` is emitted for parsed FBNS `fbpushnotif` payloads.
* FBNS also emits the notification `collapse_key` as an event name when present, for example `direct_v2_message`.
* FBNS emits `reg_response`, `registered`, `logging`, and `pp` for registration and lower-level broker payloads.
