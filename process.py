import random
from time import sleep
import rpyc
from rpyc.utils.server import ThreadedServer
from typing import List, Literal, Tuple
import _thread
from typing import Callable
import rpyc
import critical_section
from helpers import R


def rpyc_exec(port: int, fn: Callable[['ProcessServiceType'], R]) -> R:
  conn = rpyc.connect('localhost', port)
  return fn(conn)


# Class to help with typing when referencing to the exposed functions
class ProcessServiceType:
  root: 'ProcessService'


class ProcessService(rpyc.Service):
  def __init__(self, process: 'Process') -> None:
    super().__init__()
    self.process = process

  def exposed_get_state(self):
    return self.process.state

  def exposed_get_id(self):
    return self.process.id

  # For testing purposes
  def exposed_acquire_critical_section(self) -> bool:
    return self.process.acquire_critical_section()

  def exposed_release_critical_section(self):
    return self.process.release_critical_section()

  def exposed_get_timeout_interval(self) -> Tuple[int, int]:
    return self.process.timeout_interval

  def exposed_set_timeout_interval_upper_bound(self, interval_upper_bound: int) -> Tuple[int, int]:
    return self.process.set_timeout_interval_upper_bound(interval_upper_bound)


class Process:
  def __init__(self, id: int, port: int, other_processes_ports: List[int], critical_section_port: int) -> None:
    self.id = id
    self.port = port
    self.other_processes_ports = other_processes_ports
    self.critical_section_port = critical_section_port
    self.state: Literal['DO-NOT-WANT', 'WANTED', 'HELD'] = 'DO-NOT-WANT'
    self.timeout_interval: Tuple[int, int] = [5, 5]

  def acquire_critical_section(self):
    # Process needs to be in WANTED state
    if self.state != 'WANTED':
      return False

    # If acquiring critical section fails, e.g. the method returns False, don't change the state
    if not critical_section.rpyc_exec(self.critical_section_port, lambda conn: conn.root.exposed_acquire_critical_section(self.port)):
      return False
    self.state = 'HELD'
    return True

  def release_critical_section(self):
    self.state = 'DO-NOT-WANT'
    # After releasing, start the timeout again
    _thread.start_new_thread(self.timeout, ())

  # starts a thread that runs the process's ThreadedServer
  def start(self):
    _thread.start_new_thread(self.run, ())
    _thread.start_new_thread(self.timeout, ())

  def run(self):
    t = ThreadedServer(ProcessService(self), port=self.port)
    t.start()

  def set_timeout_interval_upper_bound(self, interval_upper_bound: int):
    self.timeout_interval = [self.timeout_interval[0], interval_upper_bound]
    return self.timeout_interval

  def timeout(self):
    # Pick timeout as random int from the interval
    timeout = random.choice(
        range(self.timeout_interval[0], self.timeout_interval[1] + 1))
    sleep(timeout)

    self.start_acquiring_critical_section()

  def start_acquiring_critical_section(self):
    # Process needs to be in DO-NOT-WANT state to transition to WANTED
    if self.state != 'DO-NOT-WANT':
      return

    self.state = 'WANTED'
    return
