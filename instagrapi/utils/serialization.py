import datetime
import enum
import json
from typing import Any, TypeVar, Union, overload


class InstagrapiJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, enum.Enum):
            return obj.value
        elif isinstance(obj, datetime.time):
            return obj.strftime("%H:%M")
        elif isinstance(obj, (datetime.datetime, datetime.date)):
            return int(obj.strftime("%s"))
        elif isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


T = TypeVar("T")


# Overload for when no default is provided - could return Any or None
@overload
def json_value(data: dict, *args: Union[str, int]) -> Any: ...


# Overload for when default is provided - returns either found value or default type
@overload
def json_value(data: dict, *args: Union[str, int], default: T) -> Union[T, Any]: ...


def json_value(data: dict, *args: Union[str, int], default: Any = None) -> Any:
    """Navigate through nested dictionaries/lists using provided keys.

    Args:
        data: The dictionary to navigate
        *args: Keys/indices to navigate through (strings for dicts, ints for lists)
        default: Value to return if navigation fails

    Returns:
        The value found at the specified path, or default if not found
    """
    cur: Any = data
    for a in args:
        try:
            if isinstance(a, int):
                cur = cur[a]
            else:
                cur = cur.get(a)
            if cur is None:
                return default
        except (IndexError, KeyError, TypeError, AttributeError):
            return default
    return cur


def dumps(data):
    """Json dumps format as required Instagram"""
    return InstagrapiJSONEncoder(separators=(",", ":")).encode(data)
