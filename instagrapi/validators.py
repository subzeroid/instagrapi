import datetime
from pathlib import Path
from typing import (
    # Union, get_origin,
    get_type_hints, get_args
)


class ValidationError(Exception):
    pass


class PathNotExistsError(ValidationError):
    pass


class PathNotAFileError(ValidationError):
    pass


class HttpUrlError(ValidationError):
    pass


class HttpUrl(str):
    prefixes = ('http', 'https')
    max_length = 2083

    def __init__(self, value: str):
        if not value.startswith(self.prefix):
            raise HttpUrlError(f'URL "{value}" must been start from http')
        if len(value) > self.max_length:
            raise HttpUrlError(
                f'URL "{value}" is very large'
                f'(max={self.max_length}, current={len(value)})'
            )
        return value


class FilePath(Path):

    def __init__(self, value: Path):
        if not isinstance(value, Path):
            value = Path(value)
        if not value.is_file():
            raise PathNotAFileError(f'Path "{value}" not a file')
        if not value.exists():
            raise PathNotExistsError(f'Path "{value}" not found')
        return value


class Datetime(datetime.datetime):

    @classmethod
    def validate(cls, value: datetime.datetime) -> datetime.datetime:
        if not isinstance(value, datetime.datetime):
            value = datetime.datetime.fromtimestamp(value)
        return value


class BaseModel:
    _hints = {}
    _errors = []

    def __init__(self, *args, **kwargs):
        self._errors = []
        self._hints = get_type_hints(self)
        nl, tab = '\n', '    '
        for key, hint in self._hints.items():
            try:
                val = kwargs[key]
            except KeyError:
                self._errors.append(
                    f'{key}{nl}{tab}field required (type={hint})'
                )
                continue
            types = get_args(hint) or (hint, )
            if not isinstance(val, types):
                try:
                    # baes_type = types[0]
                    # if hasattr(base_type, 'validate')
                    # if types[0] == datetime.datetime:
                    #     val = datetime.datetime.fromtimestamp(val)
                    # else:
                    val = types[0](val)
                except Exception:
                    # import pudb;pudb.set_trace()
                    self._errors.append(
                        f'{key}{nl}{tab}type error (type={hint})'
                        f'{nl}{tab}now {key}="{val}" (type={type(val)})'
                    )
                continue
            setattr(self, key, val)
        if self._errors:
            raise ValidationError(
                f'{len(self._errors)} validation errors '
                f'for {type(self).__name__}{nl}'
                f'{nl.join(self._errors)}'
            )

    def __repr__(self):
        return getattr(
            self, 'pk', getattr(
                self, 'id', getattr(
                    self, 'name', self.dict()
                )
            )
        )

    def dict(self):
        return {
            key: getattr(self, key)
            for key in self._hints.keys()
        }
