# pydargs

Pydargs converts a dataclass to command line arguments in argparse.

## Installation

Pydargs can be installed with your favourite package manager. For example:

```
pip install pydargs
```

## Usage

A minimal usage example would be:

```python
from dataclasses import dataclass
from pydargs import parse


@dataclass
class Config:
    number: int
    some_string: str = "abc"

if __name__ == "__main__":
    config = parse(Config)
```

After which this entrypoint can be called with

```shell
entrypoint --number 42
```
or
```shell
entrypoint --number 42 --some-string abcd
```

## Supported Types

The base types are supported: `int`, `float`, `str`, `bool`, as well as:

- **Enums** or **literals** comprised of those types.
- **Date** and **datetime**, with an optional `date_format` metadata
  field: `your_date: date = field(metadata=dict(date_format="%m-%d-%Y"))`. When not
  provided dates in ISO 8601 format are accepted.
- **Lists** of those types, either denoted as e.g. `list[int]` or `typing.Sequence[int]`.
  Multiple arguments to a `numbers: list[int]` field can be provided as `--numbers 1 2 3`.
- **Optional types**, denoted as e.g. `typing.Optional[int]` or `int | None` (for Python 3.10 and above).
  Any argument passed is assumed to be of the provided type and can never be `None`.
- **Unions of types**, denoted as e.g. `typing.Union[int, str]` or `int | str`. Each argument
  will be parsed into the first type that returns a valid result. Note that this means
  that `str | int` will _always_ result in a value of type `str`.
- Any other type that can be instantiated from a string, such as `Path`.
