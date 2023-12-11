# pydargs

Pydargs allows configuring a dataclass through command line arguments.

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
- **Lists** of those types, either denoted as e.g. `list[int]` or `Sequence[int]`.
  Multiple arguments to a `numbers: list[int]` field can be provided as `--numbers 1 2 3`.
  A list-field without a default will require at least a single value to be provided.
  If a default is provided, it will be completely replaced by any arguments, if provided.
- **Optional types**, denoted as e.g. `typing.Optional[int]` or `int | None` (for Python 3.10 and above).
  Any argument passed is assumed to be of the provided type and can never be `None`.
- **Unions of types**, denoted as e.g. `typing.Union[int, str]` or `int | str`. Each argument
  will be parsed into the first type that returns a valid result. Note that this means
  that `str | int` will _always_ result in a value of type `str`.
- Any other type that can be instantiated from a string, such as `Path`.

## Metadata

### Ignoring fields
Fields can be ignored by adding the `ignore_arg` metadata field:
```python
@dataclass
class Config:
    number: int
    ignored: str = field(metadata=dict(ignore_arg=True))
```
When indicated, this field is not added to the parser and cannot be overridden with an argument.
