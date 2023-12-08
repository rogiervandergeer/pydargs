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

### Metadata

Additional options can be provided to the dataclass field metadata.

The following metadata fields are supported:

#### `as_flags`

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

#### `parser`

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
