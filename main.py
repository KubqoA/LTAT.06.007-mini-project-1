import sys
from typing import Callable, Dict
from helpers import handle_cmd_with_int_argument


def list():
  print('list')
  pass


def set_time_to_critical_section(time: int):
  print('set_time_to_critical_section: %d' % time)
  pass


def set_time_out_interval(timeout: int):
  print('set_time_out_interval: %d' % timeout)
  pass


if __name__=='__main__':
  # Check for correctness of provided arguments
  if len(sys.argv) != 2 or not sys.argv[1].isdigit():
    print("Usage: %s [number_of_processes]" % sys.argv[0], file=sys.stderr)
    sys.exit(1)

  n = int(sys.argv[1])
  print("Launching %d processes" % n)

  # Start= the command line interface
  while True:
    try:
      user_input = input("$ ")
    except EOFError as e:
      # handle Ctrl+d as end of program
      print()
      sys.exit(1)

    cmd = user_input.split(' ', 1)[0]

    # Define the handlers for commands
    handlers: Dict[str, Callable[[], None]] = {
      'help': lambda: print('Supported commands: list, time-cs [t], time-p [t], help, exit'),
      'exit': lambda: sys.exit(0),
      'list': list,
      'time-cs': handle_cmd_with_int_argument(user_input, set_time_to_critical_section, 'time-cs [t]'),
      'time-p': handle_cmd_with_int_argument(user_input, set_time_out_interval, 'time-p [t]'),
    }

    # Execute appropriate handler or print error message
    handlers.get(cmd, lambda: len(cmd) > 0 and not cmd.isspace() and print('%s: command not found' % cmd))()
