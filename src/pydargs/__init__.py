import sys
from argparse import ArgumentParser, BooleanOptionalAction, Namespace, SUPPRESS
from collections.abc import Sequence
from dataclasses import MISSING, fields
from datetime import date, datetime
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    get_origin,
    get_args,
)
from warnings import warn

from pydargs.utils import named_partial, rename


UNION_TYPES: set[Any] = {Union}
if sys.version_info >= (3, 10):
    from types import UnionType

    UNION_TYPES.add(UnionType)


class DataClassProtocol(Protocol):
    __dataclass_fields__: ClassVar[dict]


Dataclass = TypeVar("Dataclass", bound=DataClassProtocol)


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
    return _create_object(tp, namespace)


def _create_object(tp: Type[Dataclass], namespace: Namespace, prefix: str = "") -> Dataclass:
    for field in fields(tp):
        if hasattr(field.type, "__dataclass_fields__"):
            # Create nested dataclass object
            setattr(
                namespace,
                prefix + field.name,
                _create_object(field.type, namespace, prefix=f"{prefix}{field.name}_"),
            )
    args = {key[len(prefix) :]: value for key, value in namespace.__dict__.items() if key.startswith(prefix)}
    # Remove the keys used so far from the namespace, to prevent clutter when creating a parent object.
    for key in args.keys():
        delattr(namespace, prefix + key)
    return tp(**args)


def _create_parser(tp: Type[Dataclass], **kwargs: Any) -> ArgumentParser:
    parser = ArgumentParser(**kwargs, argument_default=SUPPRESS)
    _add_arguments(parser, tp)
    return parser


def _add_arguments(parser: ArgumentParser, tp: Type[Dataclass], prefix: str = "") -> ArgumentParser:
    parser_or_group = parser.add_argument_group(prefix.strip("_")) if prefix else parser
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
            arguments = [prefix + field.name]
            if field_has_default:
                # Positional arguments that are not required must have a valid default
                argument_kwargs["default"] = (
                    field.default_factory()  # This is safe only because the parser is only used once.
                    if field.default_factory is not MISSING
                    else field.default
                )
                argument_kwargs["nargs"] = "?"

        else:
            arguments = [f"--{(prefix+field.name).replace('_', '-')}"]
            if short_option:
                arguments = [short_option] + arguments
            argument_kwargs["dest"] = prefix + field.name
            argument_kwargs["required"] = not field_has_default

        if parser_fct := field.metadata.get("parser", None):
            parser_or_group.add_argument(
                *arguments,
                type=parser_fct,
                **argument_kwargs,
            )
        elif origin := get_origin(field.type):
            if origin is Sequence or origin is list:
                argument_kwargs["nargs"] = "*" if field_has_default else "+"
                parser_or_group.add_argument(
                    *arguments,
                    type=get_args(field.type)[0],
                    **argument_kwargs,
                )
            elif origin is Literal:
                if len({type(arg) for arg in get_args(field.type)}) > 1:
                    raise NotImplementedError("Parsing Literals with mixed types is not supported.")
                parser_or_group.add_argument(
                    *arguments,
                    choices=get_args(field.type),
                    type=type(get_args(field.type)[0]),
                    **argument_kwargs,
                )
            elif origin in UNION_TYPES:
                parser_or_group.add_argument(
                    *arguments,
                    type=named_partial(_parse_union, _display_name=repr(field.type), union_type=field.type),
                    **argument_kwargs,
                )
            else:
                raise NotImplementedError(f"Parsing into type {origin} is not implemented.")
        elif hasattr(field.type, "__dataclass_fields__"):
            if positional:
                raise ValueError("Dataclasses may not be positional arguments.")
            if field.default_factory is not None and field.default_factory != field.type:
                warn(f"Non-standard default of field {field.name} is ignored by pydargs.", UserWarning)
            # Recursively add arguments for the nested dataclasses
            _add_arguments(parser, field.type, prefix=f"{prefix}{field.name}_")
        elif field.type in (date, datetime):
            parser_or_group.add_argument(
                *arguments,
                type=named_partial(
                    _parse_datetime,
                    _display_name=str(field.type),
                    is_date=field.type is date,
                    date_format=field.metadata.get("date_format"),
                ),
                **argument_kwargs,
            )
        elif field.type is bool:
            if field.metadata.get("as_flags", False):
                if positional:
                    raise ValueError("A field cannot be positional as well as be represented by flags.")
                parser_or_group.add_argument(
                    *arguments,
                    action=BooleanOptionalAction,
                    **argument_kwargs,
                )
            else:
                parser_or_group.add_argument(
                    *arguments,
                    type=_parse_bool,
                    **argument_kwargs,
                )
        elif issubclass(field.type, Enum):
            parser_or_group.add_argument(
                *arguments,
                choices=list(field.type),
                type=named_partial(_parse_enum_key, _display_name=field.type.__name__, enum_type=field.type),
                **argument_kwargs,
            )
        elif field.type is bytes:
            encoding = field.metadata.get("encoding", "utf-8")
            parser_or_group.add_argument(
                *arguments,
                type=named_partial(field.type, _display_name=encoding, encoding=encoding),
                **argument_kwargs,
            )
        else:
            parser_or_group.add_argument(
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


def _parse_enum_key(key: str, enum_type: Type[Enum]) -> Enum:
    try:
        return enum_type[key]
    except KeyError:
        raise TypeError


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
