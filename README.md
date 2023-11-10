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
