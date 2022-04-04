import sys
from typing import Callable, Dict, List
from helpers import handle_cmd_with_int_argument, is_debug
import process
import critical_section
from functools import partial


def list(processes_ports: List[int]):
  for port in processes_ports:
    process.rpyc_exec(port, lambda conn: print("P%d: %s" % (
        conn.root.exposed_get_id(), conn.root.exposed_get_state())))


def set_time_to_critical_section(critical_section_port: int, release_upper_bound: int):
  current_interval = critical_section.rpyc_exec(
      critical_section_port, lambda conn: conn.root.exposed_get_release_interval())
  if release_upper_bound < current_interval[0]:
    print('New release interval upper bound cannot be lower than the interval start. Current interval: ', current_interval)
    return

  interval = critical_section.rpyc_exec(
      critical_section_port, lambda conn: conn.root.exposed_set_release_interval_upper_bound(release_upper_bound))
  print('Release interval changed, new interval:', interval)


def set_time_out_interval_process(timeout_upper_bound: int, conn: process.ProcessServiceType):
  id = conn.root.exposed_get_id()
  current_interval = conn.root.exposed_get_timeout_interval()
  if timeout_upper_bound < current_interval[0]:
    print('P%d: New timeout interval upper bound is higher than current interval start. Current interval: ' %
          id, current_interval)
    return

  interval = conn.root.exposed_set_timeout_interval_upper_bound(
      timeout_upper_bound)
  print('P%d: Timeout interval changed, new interval:' % id, interval)


def set_time_out_interval(processes_ports: List[int], timeout_upper_bound: int):
  for port in processes_ports:
    process.rpyc_exec(port, partial(
        set_time_out_interval_process, timeout_upper_bound))


def acquire(processes_ports: List[int], id: int):
  if id >= len(processes_ports):
    print('Process with id=%d, does not exist' % id)
    return

  if process.rpyc_exec(
          processes_ports[id], lambda conn: conn.root.exposed_acquire_critical_section()):
    print('P%d: Acquired critical section' % id)
  else:
    print('P%d: Could not acquire critical section' % id)


def launch_processes(n: int, basePort: int = 18812) -> List[int]:
  # First start the service for the critical section
  critical_section.CriticalSection(basePort).start()

  # Then start the processes
  basePortForProcesses = basePort + 1
  ports = [basePortForProcesses + id for id in range(0, n)]
  for id, port in enumerate(ports):
    process.Process(id, port, ports[:id]+ports[id+1:], basePort).start()
  return [basePort, ports]


if __name__ == '__main__':
  # Check for correctness of provided arguments
  if len(sys.argv) != 2 or not sys.argv[1].isdigit():
    print("Usage: %s [number_of_processes]" % sys.argv[0], file=sys.stderr)
    sys.exit(1)

  n = int(sys.argv[1])
  print("Launching %d processes" % n)
  [critical_section_port, processes_ports] = launch_processes(n)

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
        'help': lambda: print('Supported commands: list, time-cs [t], time-p [t], help, whoami, exit'),
        'exit': lambda: sys.exit(0),
        'whoami': lambda: print('Jakub Arbet, C20301'),
        'list': partial(list, processes_ports),
        'time-cs': handle_cmd_with_int_argument(user_input, partial(set_time_to_critical_section, critical_section_port), 'time-cs [t]'),
        'time-p': handle_cmd_with_int_argument(user_input, partial(set_time_out_interval, processes_ports), 'time-p [t]'),
    }

    # Special acquire command for testing and debugging purposes
    # Forces, if pre-conditions are met, the specified process id to acquire critical section
    if is_debug():
      handlers['acquire'] = handle_cmd_with_int_argument(
          user_input, partial(acquire, processes_ports), 'acquire [id]')

    # Execute appropriate handler or print error message
    handlers.get(cmd, lambda: len(cmd) > 0 and not cmd.isspace()
                 and print('%s: command not found' % cmd))()
