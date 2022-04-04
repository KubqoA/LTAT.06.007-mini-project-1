import rpyc
from rpyc.utils.server import ThreadedServer
from typing import List
import _thread


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


class Process:
  def __init__(self, id: int, port: int, other_processes_ports: List[int]) -> None:
    self.id = id
    self.port = port
    self.other_processes_ports = other_processes_ports
    self.state: str = 'DO-NOT-WANT'
  
  # starts a thread that runs the process's ThreadedServer
  def start(self):
    _thread.start_new_thread(self.run, ())
  
  def run(self):
    t=ThreadedServer(ProcessService(self), port=self.port)
    t.start()
