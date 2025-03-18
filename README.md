# PLC Programming with Python on Unipi 1.1 and Raspberry Pi

This repository holds a package `unipi` to emulate a PLC, while the PLC programs 
are written in pure Python. To test the package and play with it, an Unipi 1.1 
PLC board with Raspberry 3 was used. Communication with the board is done with 
the EVOK 3 API from Unipi.

Class `GPIO` in module `gpio.py` of the package is the underlying module 
responsible for the connection between the Python program and the EVOK 3 API of 
Unipi. However, to write a PLC application the core class is `AbstractPLC` in 
module `plc.py`. Every PLC application inherits from this class and should 
implement the abstract methods of this core class.

Some application examples can be found in the folder `applications` of this 
repository.
