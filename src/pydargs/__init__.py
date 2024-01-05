import argparse
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from dataclasses import MISSING, dataclass, fields
from datetime import date, datetime
from enum import Enum
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

from pydargs.utils import named_partial, rename


UNION_TYPES: set[Any] = {Union}
if sys.version_info >= (3, 10):
    from types import UnionType

    UNION_TYPES.add(UnionType)


@dataclass
class ADataclass(Protocol):
    ...


Dataclass = TypeVar("Dataclass", bound=ADataclass)


def parse(tp: Type[Dataclass], args: Optional[list[str]] = None, **kwargs: Any) -> Dataclass:
    """Instantiate an object of the provided dataclass type from command line arguments.

    Args:
        tp: Type of the object to instantiate. This is expected to be a dataclass.
        args: Optional list of arguments. Defaults to sys.argv.
        **kwargs: Keyword arguments passed to the ArgumentParser object.

    Returns:
        An instance of tp.
    """
    namespace = _create_parser(tp, **kwargs).parse_args(args)
    return tp(**namespace.__dict__)


def _create_parser(tp: Type[Dataclass], **kwargs: Any) -> ArgumentParser:
    parser = ArgumentParser(**kwargs, argument_default=argparse.SUPPRESS)
    for field in fields(tp):
        if field.metadata.get("ignore_arg", False):
            continue

        argument_kwargs: dict[str, Any] = dict()
        field_has_default = field.default is not MISSING or field.default_factory is not MISSING
        argument_kwargs["help"] = field.metadata.get("help", "")
        if field.default is not MISSING:
            if len(argument_kwargs["help"]):
                argument_kwargs["help"] += " "
            argument_kwargs["help"] += f"(default: {field.default})"
        if "metavar" in field.metadata:
            argument_kwargs["metavar"] = field.metadata["metavar"]
        positional = field.metadata.get("positional", False)
        short_option = field.metadata.get("short_option")
        if positional:
            if short_option:
                raise ValueError("Short options are not supported for positional arguments.")
            arguments = [field.name]
            if field_has_default:
                # Positional arguments that are not required must have a valid default
                argument_kwargs["default"] = (
                    field.default_factory()  # This is safe only because the parser is only used once.
                    if field.default_factory is not MISSING
                    else field.default
                )
                argument_kwargs["nargs"] = "?"

        else:
            arguments = [f"--{field.name.replace('_', '-')}"]
            if short_option:
                arguments = [short_option] + arguments
            argument_kwargs["dest"] = field.name
            argument_kwargs["required"] = not field_has_default

        if parser_fct := field.metadata.get("parser", None):
            parser.add_argument(
                *arguments,
                type=parser_fct,
                **argument_kwargs,
            )
        elif origin := get_origin(field.type):
            if origin is Sequence or origin is list:
                argument_kwargs["nargs"] = "*" if field_has_default else "+"
                parser.add_argument(
                    *arguments,
                    type=get_args(field.type)[0],
                    **argument_kwargs,
                )
            elif origin is Literal:
                if len({type(arg) for arg in get_args(field.type)}) > 1:
                    raise NotImplementedError("Parsing Literals with mixed types is not supported.")
                parser.add_argument(
                    *arguments,
                    choices=get_args(field.type),
                    type=type(get_args(field.type)[0]),
                    **argument_kwargs,
                )
            elif origin in UNION_TYPES:
                parser.add_argument(
                    *arguments,
                    type=named_partial(_parse_union, name=repr(field.type), union_type=field.type),
                    **argument_kwargs,
                )
            else:
                raise NotImplementedError(f"Parsing into type {origin} is not implemented.")
        elif field.type in (date, datetime):
            parser.add_argument(
                *arguments,
                type=named_partial(
                    _parse_datetime,
                    is_date=field.type is date,
                    date_format=field.metadata.get("date_format"),
                    name=str(field.type),
                ),
                **argument_kwargs,
            )
        elif field.type is bool:
            if field.metadata.get("as_flags", False):
                if positional:
                    raise ValueError("A field cannot be positional as well as be represented by flags.")
                parser.add_argument(
                    *arguments,
                    action=argparse.BooleanOptionalAction,
                    **argument_kwargs,
                )
            else:
                parser.add_argument(
                    *arguments,
                    type=_parse_bool,
                    **argument_kwargs,
                )
        elif issubclass(field.type, Enum):
            parser.add_argument(
                *arguments,
                choices=list(field.type),
                type=lambda x: field.type[x],
                **argument_kwargs,
            )
        elif field.type is bytes:
            encoding = field.metadata.get("encoding", "utf-8")
            parser.add_argument(
                *arguments,
                type=named_partial(field.type, encoding=encoding, name=encoding),
                **argument_kwargs,
            )
        else:
            parser.add_argument(
                *arguments,
                type=field.type,
                **argument_kwargs,
            )
    return parser


@rename(name="bool")
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
