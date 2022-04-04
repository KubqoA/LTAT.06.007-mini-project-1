import sys
from typing import Callable, Dict, List
from helpers import handle_cmd_with_int_argument
import process
import critical_section
from functools import partial


def list(processes_ports: List[int]):
  for port in processes_ports:
    process.rpyc_exec(port, lambda conn: print("P%d: %s" % (conn.root.exposed_get_id(), conn.root.exposed_get_state())))


def set_time_to_critical_section(processes_ports: List[int], time: int):
  print('set_time_to_critical_section: %d' % time)
  pass


def set_time_out_interval(processes_ports: List[int], timeout: int):
  print('set_time_out_interval: %d' % timeout)
  pass


def launch_processes(n: int, basePort: int = 18812) -> List[int]:
  # First start the service for the critical section
  critical_section.CriticalSection(basePort).start()

  # Then start the processes
  basePortForProcesses = basePort + 1
  ports = [basePortForProcesses + id for id in range(0, n)]
  for id, port in enumerate(ports):
    process.Process(id, port, ports[:id]+ports[id+1:], basePort).start()
  return ports


if __name__=='__main__':
  # Check for correctness of provided arguments
  if len(sys.argv) != 2 or not sys.argv[1].isdigit():
    print("Usage: %s [number_of_processes]" % sys.argv[0], file=sys.stderr)
    sys.exit(1)

  n = int(sys.argv[1])
  print("Launching %d processes" % n)
  processes_ports = launch_processes(n)

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
      'list': partial(list, processes_ports),
      'time-cs': handle_cmd_with_int_argument(user_input, partial(set_time_to_critical_section, processes_ports), 'time-cs [t]'),
      'time-p': handle_cmd_with_int_argument(user_input, partial(set_time_out_interval, processes_ports), 'time-p [t]'),
    }

    # Execute appropriate handler or print error message
    handlers.get(cmd, lambda: len(cmd) > 0 and not cmd.isspace() and print('%s: command not found' % cmd))()
