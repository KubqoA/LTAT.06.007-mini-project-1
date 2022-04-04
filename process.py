import random
from time import sleep
import rpyc
from rpyc.utils.server import ThreadedServer
from typing import List, Literal, Set, Tuple
import _thread
from typing import Callable
import rpyc
import critical_section
from helpers import R, is_debug


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

  def exposed_send_ok(self, payload: Tuple[int, int]):
    self.process.receive_ok(payload)

  def exposed_send_request(self, payload: Tuple[int, int]):
    self.process.receive_request(payload)


class Process:
  def __init__(self, id: int, port: int, other_processes_ports: List[int], critical_section_port: int) -> None:
    self.id = id
    self.port = port
    self.other_processes_ports = other_processes_ports
    self.critical_section_port = critical_section_port
    self.state: Literal['DO-NOT-WANT', 'WANTED', 'HELD'] = 'DO-NOT-WANT'
    self.timeout_interval: Tuple[int, int] = [5, 5]

    # Logical clock of a process
    self.logical_clock: int = 0
    self.broadcast_timestamp: int = 0

    # Set of process ports that replied okay
    self.ok_responses: Set[int] = set()

    # Queue consisting of ports of other processes that requested access
    # but their logical clock at the time was lower
    self.queue: List[int] = []

  def debug_print(self, *args):
    if is_debug():
      print('P%d [logical_clock=%d, broadcast_timestamp=%d, state=%s]:' %
            (self.id, self.logical_clock, self.broadcast_timestamp, self.state), *args)

  def acquire_critical_section(self):
    # Process needs to be in WANTED state
    if self.state != 'WANTED':
      return False

    # If acquiring critical section fails, e.g. the method returns False, don't change the state
    if not critical_section.rpyc_exec(self.critical_section_port, lambda conn: conn.root.exposed_acquire_critical_section(self.port)):
      return False
    self.logical_clock += 1
    self.state = 'HELD'
    self.debug_print('Acquired critical section')
    return True

  def release_critical_section(self):
    self.logical_clock += 1

    # Send "ok" to queued processes
    for process_port in self.queue:
      rpyc_exec(process_port, lambda conn: conn.root.exposed_send_ok(
          [self.logical_clock, self.port]))

    # Reset state
    self.state = 'DO-NOT-WANT'
    self.queue = []
    self.ok_responses = set()

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

    # Switch state and broadcast the request to acquire critical section
    # to other processes
    self.logical_clock += 1
    self.state = 'WANTED'
    self.broadcast_request()

  def broadcast_request(self):
    self.broadcast_timestamp = self.logical_clock
    for process_port in self.other_processes_ports:
      rpyc_exec(process_port, lambda conn: conn.root.exposed_send_request(
          [self.broadcast_timestamp, self.port]))

  def receive_ok(self, payload: Tuple[int, int]):
    timestamp, sender_process_port = payload
    self.debug_print('received ok from', sender_process_port)

    # increase my logical clock
    self.logical_clock = max(timestamp, self.logical_clock) + 1

    # Record the sender process port to ok repsonses set
    self.ok_responses.add(sender_process_port)

    # If we have as many responses as there are other processes acquire critical section
    if len(self.other_processes_ports) <= len(self.ok_responses):
      self.acquire_critical_section()

  def receive_request(self, payload: Tuple[int, int]):
    timestamp, sender_process_port = payload
    self.debug_print("request from", sender_process_port,
                     "timestamp", timestamp)

    # If the state is HELD, or the state is WANTED and broadcast timestamp is less than the receiving timestamp
    # add the request to queue
    # In case the timestamps are equal lower process ID (port) takes precedence
    if self.state == 'HELD' or \
        (self.state == 'WANTED' and self.broadcast_timestamp < timestamp) or \
            (self.state == 'WANTED' and self.broadcast_timestamp == timestamp and self.port < sender_process_port):
      self.debug_print('queueing', sender_process_port)
      self.queue.append(sender_process_port)

    else:
      self.debug_print('replying ok', sender_process_port)
      rpyc_exec(sender_process_port,
                lambda conn: conn.root.exposed_send_ok([timestamp + 1, self.port]))

    # increase my logical clock
    self.logical_clock = max(timestamp, self.logical_clock) + 1
