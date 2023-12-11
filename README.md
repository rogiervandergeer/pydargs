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

Additional options can be provided to the dataclass field metadata.

The following metadata fields are supported:

### `as_flags`

Set `as_flags=True` for a boolean field:
```python
from dataclasses import dataclass, field

@dataclass
class Config:
  verbose: bool = field(default=False, metadata=dict(as_flags=True))
```
which would create the arguments `--verbose` and `--no-verbose` to
set the value of `verbose` to `True` or `False` respectively, instead
of a single option that requires a value like `--verbose True`.

### `parser`

Provide a custom type converter that parses the argument into the desired type. For example:

```python
from dataclasses import dataclass, field
from json import loads

@dataclass
class Config:
  list_of_numbers: list[int] = field(metadata=dict(parser=loads))
```

This would parse `--list-of-numbers [1, 2, 3]` into the list `[1, 2, 3]`. Note that the error message returned
when providing invalid input is lacking any details. Also, no validation is performed to verify that the returned
type matches the field type. In the above example, `--list-of-numbers '{"a": "b"}'` would result in `list_of_numbers`
being the dictionary `{"a": "b"}` without any kind of warning.

### Ignoring fields
Fields can be ignored by adding the `ignore_arg` metadata field:

```python
@dataclass
class Config:
    number: int
    ignored: str = field(metadata=dict(ignore_arg=True))
```
When indicated, this field is not added to the parser and cannot be overridden with an argument.
