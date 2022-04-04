import rpyc
from rpyc.utils.server import ThreadedServer
from typing import List, Literal
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

  def exposed_release_critical_section(self):
    return self.process.release_critical_section()


class Process:
  def __init__(self, id: int, port: int, other_processes_ports: List[int], critical_section_port: int) -> None:
    self.id = id
    self.port = port
    self.other_processes_ports = other_processes_ports
    self.critical_section_port = critical_section_port
    self.state: Literal['DO-NOT-WANT', 'WANTED', 'HELD'] = 'DO-NOT-WANT'

  def acquire_critical_section(self):
    # If acquiring critical section fails, e.g. the method returns False, don't change the state
    if not critical_section.rpyc_exec(self.critical_section_port, lambda conn: conn.root.exposed_acquire_critical_section(self.port)):
      return
    self.state = 'HELD'

  def release_critical_section(self):
    self.state = 'DO-NOT-WANT'

  # starts a thread that runs the process's ThreadedServer
  def start(self):
    _thread.start_new_thread(self.run, ())

  def run(self):
    t = ThreadedServer(ProcessService(self), port=self.port)
    t.start()
