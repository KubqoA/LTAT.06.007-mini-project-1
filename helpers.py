from typing import Callable, Union, TypeVar


R = TypeVar("R")


def handle_cmd_with_int_argument(input: str, fn: Callable[[int], R], usage: str) -> Callable[[], Union[R, None]]:
  if len(input.split(' ')) != 2 or not input.split(' ')[1].isdigit():
    return lambda: print('Usage: %s', usage)

  arg = int(input.split(' ')[1])
  return lambda: fn(arg)
