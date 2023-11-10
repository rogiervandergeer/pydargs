import sys
from argparse import ArgumentParser
from dataclasses import fields
from typing import Type, TypeVar, Optional, Protocol, ClassVar, Dict


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
        parser.add_argument(
            f"--{field.name.replace('_', '-')}",
            default=field.default,
            dest=field.name,
            help=f"Override field {field.name}.",
            type=field.type,
        )
    return parser


__all__ = ["parse"]
