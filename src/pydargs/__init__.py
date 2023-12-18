import argparse
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from dataclasses import MISSING, dataclass, fields
from datetime import date, datetime
from enum import Enum
from functools import partial
from typing import (
    Any,
    Type,
    TypeVar,
    Optional,
    Protocol,
    get_origin,
    get_args,
    Union,
    Literal,
)

UNION_TYPES: set[Any] = {Union}
if sys.version_info >= (3, 10):
    from types import UnionType

    UNION_TYPES.add(UnionType)


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
        if field.metadata.get("ignore_arg", False):
            continue

        kwargs: dict[str, Any] = dict()
        field_has_default = field.default is not MISSING or field.default_factory is not MISSING
        positional = field.metadata.get("positional", False)
        if positional:
            argument_name = field.name
            if field_has_default:
                kwargs["nargs"] = "?"
        else:
            argument_name = f"--{field.name.replace('_', '-')}"
            kwargs = dict(dest=field.name, required=not field_has_default)

        if parser_fct := field.metadata.get("parser", None):
            parser.add_argument(
                argument_name,
                default=argparse.SUPPRESS,
                help=f"Override field {field.name}.",
                type=parser_fct,
                **kwargs,
            )
        elif origin := get_origin(field.type):
            if origin is Sequence or origin is list:
                kwargs["nargs"] = "*" if field_has_default else "+"
                parser.add_argument(
                    argument_name,
                    default=argparse.SUPPRESS,
                    help=f"Override field {field.name}.",
                    type=get_args(field.type)[0],
                    **kwargs,
                )
            elif origin is Literal:
                if len({type(arg) for arg in get_args(field.type)}) > 1:
                    raise NotImplementedError("Parsing Literals with mixed types is not supported.")
                parser.add_argument(
                    argument_name,
                    choices=get_args(field.type),
                    default=field.default if positional and field_has_default else argparse.SUPPRESS,
                    help=f"Override field {field.name}.",
                    type=type(get_args(field.type)[0]),
                    **kwargs,
                )
            elif origin in UNION_TYPES:
                union_parser = partial(_parse_union, union_type=field.type)
                setattr(union_parser, "__name__", repr(field.type))
                parser.add_argument(
                    argument_name,
                    default=argparse.SUPPRESS,
                    help=f"Override field {field.name}.",
                    type=union_parser,
                    **kwargs,
                )
            else:
                raise NotImplementedError(f"Parsing into type {origin} is not implemented.")
        elif field.type in (date, datetime):
            parser.add_argument(
                argument_name,
                default=argparse.SUPPRESS,
                help=f"Override field {field.name}.",
                type=partial(
                    _parse_datetime, is_date=field.type is date, date_format=field.metadata.get("date_format")
                ),
                **kwargs,
            )
        elif field.type is bool:
            if field.metadata.get("as_flags", False):
                if positional:
                    raise ValueError("A field cannot be positional as well as be represented by flags.")
                parser.add_argument(
                    f"--{field.name.replace('_', '-')}",
                    action=argparse.BooleanOptionalAction,
                    default=argparse.SUPPRESS,
                    **kwargs,
                )
            else:
                parser.add_argument(
                    argument_name,
                    default=argparse.SUPPRESS,
                    help=f"Override field {field.name}.",
                    type=_parse_bool,
                    **kwargs,
                )
        elif issubclass(field.type, Enum):
            parser.add_argument(
                argument_name,
                choices=list(field.type),
                default=field.default if positional and field_has_default else argparse.SUPPRESS,
                help=f"Override field {field.name}.",
                type=lambda x: field.type[x],
                **kwargs,
            )

        else:
            parser.add_argument(
                argument_name,
                default=argparse.SUPPRESS,
                help=f"Override field {field.name}.",
                type=field.type,
                **kwargs,
            )
    return parser


Fct = TypeVar("Fct")


def rename(name: str):
    def _rename(f: Fct) -> Fct:
        setattr(f, "__name__", name)
        return f

    return _rename


@rename("bool")
def _parse_bool(arg: str) -> bool:
    if arg.lower() == "true" or arg == "1":
        return True
    elif arg.lower() == "false" or arg == "0":
        return False
    raise TypeError(f"Unable to convert {arg} to boolean.")


def _parse_datetime(date_string: str, is_date: bool, date_format: Optional[str] = None) -> Union[date, datetime]:
    result = datetime.strptime(date_string, date_format) if date_format else datetime.fromisoformat(date_string)
    return result.date() if is_date else result


def _parse_union(value: str, union_type: Type) -> Any:
    for arg in get_args(union_type):
        if isinstance(None, arg):
            continue
        try:
            return arg(value)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse '{value}' as one of {union_type}")


__all__ = ["parse"]
