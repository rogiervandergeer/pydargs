import argparse
import sys
from argparse import ArgumentParser
from dataclasses import MISSING, dataclass, fields
from datetime import date, datetime
from enum import Enum
from functools import partial
from typing import (
    Type,
    TypeVar,
    Optional,
    Protocol,
    get_origin,
    get_args,
    Sequence,
    Union,
    Literal,
)


@dataclass
class ADataclass(Protocol):
    ...


Dataclass = TypeVar("Dataclass", bound=ADataclass)


def parse(tp: Type[Dataclass], args: Optional[list[str]] = None) -> Dataclass:
    if args is None:
        args = sys.argv
    namespace = _create_parser(tp).parse_args(args)
    return tp(**namespace.__dict__)


def _create_parser(tp: Type[Dataclass]) -> ArgumentParser:
    parser = ArgumentParser()
    for field in fields(tp):
        if origin := get_origin(field.type):
            if origin is Sequence or origin is list:
                if field.default is MISSING and field.default_factory is MISSING:
                    raise NotImplementedError(f"Parsing {origin} without a default is not supported.")
                parser.add_argument(
                    f"--{field.name.replace('_', '-')}",
                    default=argparse.SUPPRESS,
                    dest=field.name,
                    help=f"Override field {field.name}.",
                    nargs="*",
                    type=get_args(field.type)[0],
                )
            elif origin is Literal:
                if len({type(arg) for arg in get_args(field.type)}) > 1:
                    raise NotImplementedError("Parsing Literals with mixed types is not supported.")
                parser.add_argument(
                    f"--{field.name.replace('_', '-')}",
                    choices=get_args(field.type),
                    default=argparse.SUPPRESS,
                    dest=field.name,
                    help=f"Override field {field.name}.",
                    required=field.default is MISSING and field.default_factory is MISSING,
                    type=type(get_args(field.type)[0]),
                )
            else:
                raise NotImplementedError(f"Parsing into type {origin} is not implemented.")
        elif field.type in (date, datetime):
            parser.add_argument(
                f"--{field.name.replace('_', '-')}",
                default=argparse.SUPPRESS,
                dest=field.name,
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
                        f"--{field.name.replace('_', '-')}",
                        dest=field.name,
                        help=f"Set {field.name} to True.",
                        action="store_true",
                    )
                    parser.add_argument(
                        f"--no-{field.name.replace('_', '-')}",
                        dest=field.name,
                        help=f"Set {field.name} to False.",
                        action="store_false",
                    )
                else:
                    raise ValueError(f"Misspecified bool_arg_type: {as_flags}.")
            else:
                parser.add_argument(
                    f"--{field.name.replace('_', '-')}",
                    default=field.default,
                    dest=field.name,
                    help=f"Override field {field.name}.",
                    type=_parse_bool,
                )
        elif issubclass(field.type, Enum):
            parser.add_argument(
                f"--{field.name.replace('_', '-')}",
                choices=list(field.type),
                default=argparse.SUPPRESS,
                dest=field.name,
                help=f"Override field {field.name}.",
                required=field.default is MISSING and field.default_factory is MISSING,
                type=lambda x: field.type[x],
            )

        else:
            parser.add_argument(
                f"--{field.name.replace('_', '-')}",
                default=field.default,
                dest=field.name,
                help=f"Override field {field.name}.",
                type=field.type,
            )
    return parser


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
