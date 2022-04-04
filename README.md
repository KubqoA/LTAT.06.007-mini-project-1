# Ricart & Agrawala algorithm

Implementation of Ricart & Agrawala algorithm using Python with RPC communication between processes and critical section. Course assignment for [LTAT.06.007 Distributed Systems](https://courses.cs.ut.ee/2022/ds/spring) at University of Tartu.

## Requirements
For development I used Python 3.8.10 and the following packages:
* `functools`
* `random`
* `rpyc`
* `time`
* `typing`
* `_thread`

## Start
To start use the provided shell script.
```sh
./start.sh [number_of_processes]
```

You can also start the program with debug mode active
```sh
DEBUG=true ./start.sh [number_of_processes]
```
