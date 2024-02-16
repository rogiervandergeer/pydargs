# pydargs

Pydargs allows configuring a (Pydantic) dataclass through command line arguments.

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

## ArgumentParser arguments

It's possible to pass additional arguments to the underlying `argparse.ArgumentParser` instance by providing them
as keyword arguments to the `parse` function. For example:

```python
config = parse(Config, prog="myprogram", allow_abbrev=False)
```
will disable abbreviations for long options and set the program name to `myprogram` in help messages. For an extensive list of accepted arguments, see [the argparse docs](https://docs.python.org/3/library/argparse.html#argumentparser-objects).

## Supported Field Types

The dataclass can have fields of the base types: `int`, `float`, `str`, `bool`, as well as:

- **Literals** comprised of those types.
- **Enums**, although these
  are [not recommended](https://docs.python.org/3/library/argparse.html#choices) as they do not play nice in the help
  messages. Only the enum _name_ is accepted as a valid input, not the _value_.
- **Bytes**, with an optional `encoding` metadata field:
  `a_value: bytes = field(metadata=dict(encoding="ascii"))`, which defaults to utf-8.
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
- Dataclasses that, in turn, contain fields of supported types. See [Nested Dataclasses](#nested-dataclasses).
- A union of multiple dataclasses, that in turn contain fields of supported types,
  which will be parsed in [Subparsers](#subparsers).

## Metadata

Additional options can be provided to the dataclass field metadata.

The following metadata fields are supported:

### `positional`
Set `positional=True` to create a positional argument instead of an option.

```python
from dataclasses import dataclass, field

@dataclass
class Config:
  argument: str = field(metadata=dict(positional=True))
```


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

### `short_option`

Provide a short option for a field, which can be used as an alternative to the long option.
For example,

```python
from dataclasses import dataclass, field

@dataclass
class Config:
  a_field_with_a_long_name: int = field(metadata=dict(short_option="-a"))
```

would allow using `-a 42` as an alternative to `--a-field-with-a-long-name 42`.

### Ignoring fields
Fields can be ignored by adding the `ignore_arg` metadata field:

```python
@dataclass
class Config:
    number: int
    ignored: str = field(metadata=dict(ignore_arg=True))
```
When indicated, this field is not added to the parser and cannot be overridden with an argument.

### `help`

Provide a brief description of the field, used in the help messages generated by argparse.
For example, calling `your_program -h` with the dataclass below,

```python
from dataclasses import dataclass, field

@dataclass
class Config:
  an_integer: int = field(metadata=dict(help="any integer you like"))
```

would result in a message like:

```text
usage: your_program [-h] [--an-integer AN_INTEGER]

optional arguments:
  -h, --help               show this help message and exit
  --an-integer AN_INTEGER  any integer you like
```

### `metavar`

Override the displayed name of an argument in the help messages generated by argparse,
as documented [here](https://docs.python.org/3/library/argparse.html#metavar).

For example, with the following dataclass,
```python
from dataclasses import dataclass, field

@dataclass
class Config:
  an_integer: int = field(metadata=dict(metavar="INT"))
```
calling `your_program -h` would result in a message like:

```text
usage: your_program [-h] [--an-integer INT]

optional arguments:
  -h, --help        show this help message and exit
  --an-integer INT
```

## Loading Defaults from File

Pydargs can also load defaults for the fields in your dataclass from a JSON (or YAML)-formatted file.
In order to enable this, pass the flag `load_from_file=True` to `parse`.
This will add a `--file` argument to the parser. Passing a path to a json-formatted file will trigger pydargs to load
the values from the file as defaults. Any values provided in the file will take precedence over the defaults defined
in the dataclass, but can be overwritten by their respective command line arguments.
For example, with the following contents in `defaults.json`:

```json
{
  "a": 1,
  "b": "abc"
}
```

then running this code

```python
from dataclasses import dataclass
from pydargs import parse


@dataclass
class Config:
    a: int
    b: str = "def"

if __name__ == "__main__":
    config = parse(Config, load_from_file=True)
```

with the following arguments

`entrypoint --file defaults.json --b xyz`

would result in `Config(a=1, b="xyz")`.

Note that:
- The defaults provided in the file will not be type-casted by pydargs, and hence only JSON-native types are supported.
  If required, you can add type-casting by using a pydantic dataclass.
-

## Nested Dataclasses

Dataclasses may be nested; the type of a dataclass field may be another dataclass type:

```python
from dataclasses import dataclass

@dataclass
class Config:
  field_a: int
  field_b: str = "abc"


@dataclass
class Base:
  config: Config
  verbose: bool = False
```

Argument names of fields of the nested dataclass are prefixed with the field name of the nested dataclass in the base
dataclass. Calling `pydargs.parse(Base, ["-h"])` will result in something like:

```text
usage: your_program.py [-h] --config-field-a CONFIG_FIELD_A
                            [--config-field-b CONFIG_FIELD_B]
                            [--verbose VERBOSE]

options:
  -h, --help            show this help message and exit
  --verbose VERBOSE     (default: False)

config:
  --config-field-a CONFIG_FIELD_A
  --config-field-b CONFIG_FIELD_B
                        (default: abc)

```

Please be aware of the following:
- The default (factory) of fields with a dataclass type is ignored by pydargs, which may yield unexpected results.
  E.g., in the example above, `config: Config = field(default_factory=lambda: Config(field_b="def"))` will not result in a default of "def" for field_b when parsed by pydargs.
  Instead, set `field_b: str = "def"` in the definition of `Config`.
  If you must add a default, for example for instantiating your dataclass elsewhere, do `config: Config = field(default_factory=Config)`, assuming that all fields in `Config` have a default.
- Nested dataclasses can not be positional (although _fields of_ the nested dataclass can be).
- Argument names must not collide. In the example above, the `Base` class should not contain a field named `config_field_a`.

## Subparsers

Dataclasses can contain a field with a union-of-dataclasses type, e.g.:

```python
from dataclasses import dataclass, field
from typing import Union


@dataclass
class Command1:
  field_a: int
  field_b: str = "abc"


@dataclass
class Command2:
  field_c: str = field(metadata=dict(positional=True))


@dataclass
class Base:
  command: Union[Command1, Command2]
  verbose: bool = False
```

This will result in [sub commands](https://docs.python.org/3/library/argparse.html#sub-commands)
which allow calling your entrypoint as `entrypoint --verbose Command1 --field-a 12`.

Calling `pydargs.parse(Base, ["-h"])` will result in something like:

```text
usage: your_program.py [-h] [--verbose VERBOSE] {Command1,command1,Command2,command2} ...

options:
  -h, --help            show this help message and exit
  --verbose VERBOSE     (default: False)

action:
  {Command1,command1,Command2,command2}
```

Note that:
- Also lower-case command names are accepted.
- Any dataclass can not contain more than one subcommand-field.
- Sub-commands can be nested and mixed with nested dataclasses.
- Any positional fields defined after a subcommand-field can not be parsed.
- Subparsers handle all arguments that come after the command; so all global arguments must come before the command.
  In the above example this means that  `entrypoint --verbose Command2 string`
  is valid but `entrypoint Command2 string --verbose` is not.
- Subparsers handle all arguments that come after the command; so all global arguments must come before the command.
  In the above example this means that  `entrypoint --verbose Command2 string`
  is valid but `entrypoint Command2 string --verbose` is not.
