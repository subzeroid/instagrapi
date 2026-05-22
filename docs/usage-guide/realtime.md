# Realtime MQTT

!!! warning
    Realtime MQTT support is experimental. Instagram can change this private transport without notice.

The realtime client opens Instagram's MQTToT connection for receiving live events after login.
It is useful when you need callbacks for realtime payloads instead of polling HTTP endpoints.
Use the Direct methods for sending messages, reactions, and media.

| Method | Return | Description |
| --- | --- | --- |
| `realtime_connect(transport=None)` | `RealtimeClient` | Create and connect the stateful realtime client |
| `realtime_disconnect()` | `None` | Disconnect the active realtime client |
| `realtime_on(event, handler)` | `None` | Register an event handler on the active realtime client |
| `realtime_read_once()` | `Any` | Read one packet from the active realtime client |

`RealtimeClient` also exposes lower-level helpers:

| Method | Description |
| --- | --- |
| `on(event, handler)` | Register a handler for `receive`, `message`, or `realtime_sub` |
| `graph_ql_subscribe(subscriptions)` | Publish raw GraphQL realtime subscriptions |
| `skywalker_subscribe(subscriptions)` | Publish raw Skywalker subscriptions |
| `publish_json(topic, data)` | Publish a JSON payload to a raw MQTToT topic |
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

Subscribe to raw realtime topics:

``` python
rt.graph_ql_subscribe(["<graphql-subscription>"])
rt.skywalker_subscribe(["<skywalker-subscription>"])
```

Events:

* `receive` is emitted for every decoded publish packet as `{"topic": topic, "payload": payload}`.
* `message` is emitted for message-sync payloads.
* `realtime_sub` is emitted for realtime subscription payloads.
