import argparse
import sys
from argparse import ArgumentParser
from dataclasses import fields, MISSING
from typing import (
    Type,
    TypeVar,
    Optional,
    Protocol,
    ClassVar,
    Dict,
    get_origin,
    get_args,
    Sequence,
)


class ADataclass(Protocol):
    __dataclass_fields__: ClassVar[Dict]
    __dataclass_params__: ClassVar[Dict]


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
                    raise NotImplementedError(f"Parsing {tp} without a default is not supported.")
                parser.add_argument(
                    f"--{field.name.replace('_', '-')}",
                    default=argparse.SUPPRESS,
                    dest=field.name,
                    help=f"Override field {field.name}.",
                    nargs="*",
                    type=get_args(field.type)[0],
                )
            else:
                raise NotImplementedError(f"Parsing into type {tp} is not implemented.")
        else:
            parser.add_argument(
                f"--{field.name.replace('_', '-')}",
                default=field.default,
                dest=field.name,
                help=f"Override field {field.name}.",
                type=field.type,
            )
    return parser


__all__ = ["parse"]
