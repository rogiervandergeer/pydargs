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
        if field.type is bool:
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


__all__ = ["parse"]
