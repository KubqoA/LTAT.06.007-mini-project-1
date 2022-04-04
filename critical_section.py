import random
from time import sleep
import rpyc
from rpyc.utils.server import ThreadedServer
from typing import Callable, Literal, Optional, Tuple
import _thread
import process
from helpers import R


def rpyc_exec(port: int, fn: Callable[['CriticalSectionServiceType'], R]) -> R:
  conn = rpyc.connect('localhost', port)
  return fn(conn)


# Class to help with typing when referencing to the exposed functions
class CriticalSectionServiceType:
  root: 'CriticalSectionService'


# API for communicating with the CriticalSection
# Allows a caller to acquire the critical section
class CriticalSectionService(rpyc.Service):
  def __init__(self, critical_section: 'CriticalSection') -> None:
    super().__init__()
    self.critical_section = critical_section

  def exposed_acquire_critical_section(self, process_port: int) -> bool:
    # First acquire the critical section
    if not self.critical_section.acquire_by_process_port(process_port):
      return False
    print('critical section acquired')

    # Then create a thread to release it after a time interval
    _thread.start_new_thread(self.critical_section.release_after_interval, ())
    return True

  def exposed_get_release_interval(self) -> Tuple[int, int]:
    return self.critical_section.release_interval

  def exposed_set_release_interval_upper_bound(self, interval_upper_bound: int) -> Tuple[int, int]:
    return self.critical_section.set_release_interval_upper_bound(interval_upper_bound)


class CriticalSection:
  def __init__(self, port: int) -> None:
    self.port = port
    self.release_interval: Tuple[int, int] = [10, 10]
    self.state: Literal['AVAILABLE', 'ACQUIRED'] = 'AVAILABLE'
    self.process_port: Optional[int] = None

  # Starts a thread that runs the process's ThreadedServer
  def start(self):
    _thread.start_new_thread(self.run, ())

  def run(self):
    t = ThreadedServer(CriticalSectionService(self), port=self.port)
    t.start()

  def acquire_by_process_port(self, process_port: int):
    # When acquiring the critical section no process should have access to it
    if self.process_port is not None:
      return False

    self.state = 'ACQUIRED'
    self.process_port = process_port
    return True

  def release(self):
    assert(self.process_port is not None)

    # Connect to the process and tell it to release the critical section
    process.rpyc_exec(
        self.process_port, lambda conn: conn.root.exposed_release_critical_section())

    # Mark the critical section as released
    self.state = 'AVAILABLE'
    self.process_port = None

  def release_after_interval(self):
    # Pick release interval as random int from the interval
    release = random.choice(
        range(self.release_interval[0], self.release_interval[1] + 1))
    sleep(release)

    # After the interval release the critical section
    self.release()

  def set_release_interval_upper_bound(self, interval_upper_bound: int):
    self.release_interval = [self.release_interval[0], interval_upper_bound]
    return self.release_interval
