from typing import Callable, TypeVar, Union
from process import ProcessServiceType
import rpyc

def connect_and_execute_on_port(port: int, fn: Callable[[ProcessServiceType], None]) -> None:
  conn = rpyc.connect('localhost', port)
  fn(conn)


R = TypeVar("R")
def handle_cmd_with_int_argument(input: str, fn: Callable[[int], R], usage: str) -> Callable[[], Union[R, None]]:
  if len(input.split(' ')) != 2 or not input.split(' ')[1].isdigit():
    return lambda: print('Usage: %s', usage)
  
  arg = int(input.split(' ')[1])
  return lambda: fn(arg)
