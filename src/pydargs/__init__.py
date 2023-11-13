import argparse
import sys
from argparse import _ArgumentGroup, ArgumentParser
from dataclasses import fields, MISSING, is_dataclass
from datetime import date, datetime
from functools import partial
from typing import (
    Any,
    Type,
    TypeVar,
    Optional,
    Protocol,
    ClassVar,
    Dict,
    get_origin,
    get_args,
    Sequence,
    Union,
)


class ADataclass(Protocol):
    __dataclass_fields__: ClassVar[Dict]
    __dataclass_params__: ClassVar[Dict]


Dataclass = TypeVar("Dataclass", bound=ADataclass)


def parse(tp: Type[Dataclass], args: Optional[list[str]] = None) -> Dataclass:
    if args is None:
        args = sys.argv
    parsed_args = _create_parser(tp).parse_args(args).__dict__
    return create_recursive_object(tp, parsed_args)


def create_recursive_object(tp: Type[Dataclass], parsed_args: dict[str, Any], prefix: str = "") -> Dataclass:
    args = {}
    for field in fields(tp):
        if is_dataclass(field.type):
            args[field.name] = create_recursive_object(field.type, parsed_args, prefix=f"{prefix}{field.name}-")  # type: ignore
        elif f"{prefix}{field.name}" in parsed_args:
            args[field.name] = parsed_args[f"{prefix}{field.name}"]
    return tp(**args)


def _create_parser(tp: Type[Dataclass]) -> ArgumentParser:
    parser = ArgumentParser()
    _add_arguments(tp, parser)
    return parser


def _add_arguments(tp: Type[Dataclass], parser: Union[ArgumentParser, _ArgumentGroup], prefix: str = ""):
    for field in fields(tp):
        if is_dataclass(field.type):
            _add_arguments(field.type, parser.add_argument_group(field.name), prefix=f"{prefix}{field.name}-")  # type: ignore
        if origin := get_origin(field.type):
            if origin is Sequence or origin is list:
                if field.default is MISSING and field.default_factory is MISSING:
                    raise NotImplementedError(f"Parsing {origin} without a default is not supported.")
                parser.add_argument(
                    f"--{prefix}{field.name}".replace("_", "-"),
                    default=argparse.SUPPRESS,
                    dest=f"{prefix}{field.name}",
                    help=f"Override field {field.name}.",
                    nargs="*",
                    type=get_args(field.type)[0],
                )
            else:
                raise NotImplementedError(f"Parsing into type {origin} is not implemented.")
        elif field.type in (date, datetime):
            parser.add_argument(
                f"--{prefix}{field.name}".replace("_", "-"),
                default=argparse.SUPPRESS,
                dest=f"{prefix}{field.name}",
                help=f"Override field {field.name}.",
                required=field.default is MISSING and field.default_factory is MISSING,
                type=partial(
                    _parse_datetime, is_date=field.type is date, date_format=field.metadata.get("date_format")
                ),
            )
        elif field.type is bool:
            if as_flags := field.metadata.get("as_flags", None):
                if as_flags:
                    parser.add_argument(
                        f"--{prefix}{field.name}".replace("_", "-"),
                        dest=f"{prefix}{field.name}",
                        help=f"Set {field.name} to True.",
                        action="store_true",
                    )
                    parser.add_argument(
                        f"--no-{prefix}{field.name}".replace("_", "-"),
                        dest=f"{prefix}{field.name}",
                        help=f"Set {field.name} to False.",
                        action="store_false",
                    )
                else:
                    raise ValueError(f"Misspecified bool_arg_type: {as_flags}.")
            else:
                parser.add_argument(
                    f"--{prefix}{field.name}".replace("_", "-"),
                    default=field.default,
                    dest=f"{prefix}{field.name}",
                    help=f"Override field {field.name}.",
                    type=_parse_bool,
                )
        else:
            parser.add_argument(
                f"--{prefix}{field.name}".replace("_", "-"),
                default=field.default,
                dest=f"{prefix}{field.name}",
                help=f"Override field {field.name}.",
                type=field.type,
            )


def _parse_bool(arg: str) -> bool:
    if arg.lower() == "true" or arg == "1":
        return True
    elif arg.lower() == "false" or arg == "0":
        return False
    raise TypeError(f"Unable to convert {arg} to boolean.")


def _parse_datetime(date_string: str, is_date: bool, date_format: Optional[str] = None) -> Union[date, datetime]:
    result = datetime.strptime(date_string, date_format) if date_format else datetime.fromisoformat(date_string)
    return result.date() if is_date else result


__all__ = ["parse"]
