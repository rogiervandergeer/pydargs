from functools import cache, partial
from importlib.util import find_spec
from typing import Any, Callable, TypeVar

Fct = TypeVar("Fct")


def named_partial(func: Callable[..., Any], *, _display_name: str, **kwargs) -> Callable[[str], Any]:
    # Wrapper around partial to give it a name, for argparse to provide meaningful messages
    result = partial(func, **kwargs)
    setattr(result, "__name__", _display_name)
    return result


def rename(name: str) -> Callable[[Fct], Fct]:
    # Function decorator to give a function a specific name, for argparse to provide meaningful messages
    def wrapper(f: Fct) -> Fct:
        setattr(f, "__name__", name)
        return f

    return wrapper


@cache
def yaml_available() -> bool:
    return find_spec("yaml") is not None
