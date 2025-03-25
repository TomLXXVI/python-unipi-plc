# PLC Programming with Python on the Unipi 1.1 PLC Board

This repository holds a package `unipi` to emulate a PLC, while the PLC programs 
are written in pure Python. To test the package and play with it, the Unipi 1.1 
PLC board with a Raspberry Pi 3 was used. 

The communication between the PLC board and the PLC application running on the 
Raspberry Pi happens with Unipi EVOK 3 API. Class `GPIO` in module `gpio.py` of 
the package is the underlying module which takes care of the communication 
between the Python program and the EVOK 3 API.

To write a PLC application with the `unipi` package, the core class is 
`AbstractPLC` in module `plc.py`. Every PLC application must inherit from this 
class and should implement the abstract methods of this core class (
`control_routine`, `exit_routine`, and `emergency_routine`).

Some application examples can be found in the folder `applications` of this 
repository.
