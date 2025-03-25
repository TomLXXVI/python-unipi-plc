from abc import ABC, abstractmethod
import sys
import signal
import logging
from dataclasses import dataclass
from .gpio import GPIO, DigitalInput, DigitalOutput, AnalogInput, AnalogOutput
from .exceptions import ConfigurationError, InternalCommunicationError, EmergencyException
from .email_notification import EmailNotification


@dataclass
class MemoryVariable:
    """
    Represents a variable with a memory: the variable holds its current state,
    but also remembers its previous state (from the previous PLC scan cycle). 
    This allows for edge detection. 
    
    Attributes
    ----------
    curr_state: bool | int | float
        Current state of the variable.
    prev_state: bool | int | float
        Previous state of the variable, i.e., its state in the previous PLC
        scan cycle.
    single_bit: bool
        Indicates that the memory variable should be treated as a single bit 
        variable (its value can be either 0 or 1). Default value is `True`.
    
    Methods
    -------
    update: 
        Changes the current state of the variable.
    """
    curr_state: bool | int | float = 0
    prev_state: bool | int | float = 0
    single_bit: bool = True

    def update(self, value: int | float) -> None:
        """Updates the current state of the variable with parameter `value`.
        Before `value` is assigned to the current state of the variable, the
        preceding current state is stored in attribute `prev_state`.
        """
        self.prev_state = self.curr_state
        self.curr_state = value
    
    @property
    def active(self) -> bool:
        """Returns `True` if the current state is `True`, else returns `False`."""
        if self.curr_state:
            return True
        return False
    
    def activate(self) -> None:
        """Sets the current state to `True` (1). Only for single bit variables 
        (attribute `is_binary` must be `True`; if `is_binary` is `False`, a
        `ValueError` exception is raised).
        """
        if self.single_bit:
            self.update(1)
        else:
            raise ValueError("Memory variable is not single bit.")

    def deactivate(self) -> None:
        """Sets the current state to `False` (0). Only for single bit variables 
        (attribute `is_binary` must be `True`; if `is_binary` is `False`, a
        `ValueError` exception is raised).
        """
        if self.single_bit:
            self.update(0)
        else:
            raise ValueError("Memory variable is not single bit.")
    
    @property
    def raising_edge(self) -> bool:
        """Returns `True` if `prev_state` is 0 and `curr_state` is 1. Only for 
        single bit variables (attribute `is_binary` must be `True`; if `is_binary` 
        is `False`, a `ValueError` exception is raised).
        """
        if self.single_bit:
            if self.curr_state and not self.prev_state:
                return True
            return False
        else:
            raise ValueError("Memory variable is not single bit.")

    @property
    def falling_edge(self) -> bool:
        """Returns `True` if `prev_state` is 1 and `curr_state` is 0. Only for 
        single bit variables (attribute `is_binary` must be `True`; if `is_binary` 
        is `False`, a `ValueError` exception is raised).
        """
        if self.single_bit:
            if self.prev_state and not self.curr_state:
                return True
            return False
        else:
            raise ValueError("Memory variable is not single bit.")


class AbstractPLC(ABC):
    """
    Implements the common functionality of any PLC application running on the
    Unipi 1.1 PLC board with the Unipi EVOK API.

    To write a specific PLC application, the user needs to write its own class
    that must be derived from this base class and implements the abstract
    methods of the base class.
    """
    def __init__(
        self,
        ip_address: str = "localhost",
        port: int = 8080,
        device: str | int = 1,
        eml_notification: EmailNotification | None = None
    ) -> None:
        """Creates an `AbstractPLC` instance.

        Parameters
        ----------
        ip_address:
            IP address or network name of the computer on which Unipi EVOK API 
            is running. The default name is "localhost", which means Unipi EVOK 
            API is running on the same computer as our PLC-application.
        port:
            Network port the Unipi EVOK API is listening to. The default port is
            8080.
        device:
            Name of the Unipi-device in the EVOK configuration file 
            (see: `/etc/evok/autogen.yaml`). Default for Unipi 1.1 is 1.
        eml_notification: optional
            Instance of class `EmailNotification` (see module
            email_notification.py). Allows to send email messages if certain
            events have occurred (e.g. to send an alarm).
        
        Notes
        -----
        The PLC object has an attribute `logger` that can be used to write
        messages to a log file and to the display of the terminal. See also
        `logging.py`.
        """
        # Set the base URL of the EVOK API
        # noinspection HttpUrlsUsage
        GPIO.base_url = f"http://{ip_address}:{port}/rest/"
        GPIO.device = device
        
        # Attaches the e-mail notification service (can be None).
        self.eml_notification = eml_notification

        # Attaches a logger to the PLC application (the logger can be configured
        # by calling the function `init_logger()` in module `unipi.logging.py`
        # at the start of the main program).
        self.logger = logging.getLogger("Unipi1.1-PLC")

        # Dictionaries that hold the inputs/outputs used by the PLC application.
        self._digital_inputs: dict[str, DigitalInput] = {}
        self._digital_outputs: dict[str, DigitalOutput] = {}
        self._analog_inputs: dict[str, AnalogInput] = {}
        self._analog_outputs: dict[str, AnalogOutput] = {}

        # Dictionaries where the states of inputs/outputs are stored. These are
        # the memory registries of the PLC. The program logic reads from or 
        # writes to these registries.
        self.di_state_registry: dict[str, MemoryVariable] = {}
        self.ai_state_registry: dict[str, MemoryVariable] = {}
        self.do_state_registry: dict[str, MemoryVariable] = {}
        self.ao_state_registry: dict[str, MemoryVariable] = {}

        # To terminate program: press Ctrl-Z and method `exit_handler` will be
        # called which terminates the PLC scanning loop.
        signal.signal(signal.SIGTSTP, lambda signum, frame: self.exit_handler())
        self._exit: bool = False

    def add_digital_input(
        self,
        pin: str | int,
        label: str,
        normal_closed: bool = False,
        init_value: int = 0
    ) -> MemoryVariable:
        """Adds a digital input to the PLC application.

        Parameters
        ----------
        pin:
            Sequence number of pin (based on `count` parameter in file 
            `/etc/evok/hw_definitions/UNIPI11.yaml`).
        label:
            Meaningful name for the digital input. This will be the name used
            in the PLC application to access the input.
        normal_closed:
            Indicates that the input is normally closed in its resting state.
            The default is `False`, i.e. normally open.
        init_value:
            Sets the initial value when the PLC application is starting up.
            The default is 0, i.e. OFF if the input is normally open.
        
        Returns
        -------
        The memory variable of the digital input in the digital input memory
        registry.
        """
        self._digital_inputs[label] = DigitalInput(pin, label, normal_closed)
        self.di_state_registry[label] = MemoryVariable(
            curr_state=init_value,
            prev_state=init_value
        )
        return self.di_state_registry[label]

    def add_digital_output(
        self,
        pin: str | int,
        label: str,
        init_value: int = 0
    ) -> MemoryVariable:
        """Adds a digital output to the PLC application.
        
        Parameters
        ----------
        See docstring of `add_digital_input(...)`.
        
        Returns
        -------
        The memory variable of the digital output in the digital output memory
        registry.
        """
        do = DigitalOutput(pin, label)
        self._digital_outputs[label] = do
        self.do_state_registry[label] = MemoryVariable(
            curr_state=init_value,
            prev_state=init_value
        )
        return self.do_state_registry[label]

    def add_analog_input(
        self,
        pin: str | int,
        label: str,
        init_value: float = 0.0
    ) -> MemoryVariable:
        """Adds an analog input to the PLC application.
        
        Parameters
        ----------
        See docstring of `add_digital_input(...)`.
        
        Returns
        -------
        The memory variable of the analog input in the analog input memory
        registry.
        """
        ai = AnalogInput(pin, label)
        self._analog_inputs[label] = ai
        self.ai_state_registry[label] = MemoryVariable(
            curr_state=init_value,
            prev_state=init_value
        )
        return self.ai_state_registry[label]

    def add_analog_output(
        self,
        pin: str | int,
        label: str,
        init_value: float = 0.0
    ) -> MemoryVariable:
        """Adds an analog running to the PLC application.
        
        Parameters
        ----------
        See docstring of `add_digital_input(...)`.
        
        Returns
        -------
        The memory variable of the analog running in the analog running memory
        registry.
        """
        ao = AnalogOutput(pin, label)
        self._analog_outputs[label] = ao
        self.ao_state_registry[label] = MemoryVariable(
            curr_state=init_value,
            prev_state=init_value
        )
        return self.ao_state_registry[label]

    def di_read(self, label: str) -> int:
        """Reads the current state of the digital input specified by the given
        label.

        Raises a `ConfigurationError` exception if the digital input with the
        given label has not been added to the PLC-application before.

        Returns the read value (integer). If the digital input has been
        configured as normally closed, the inverted value is returned.
        """
        di = self._digital_inputs.get(label)
        if di:
            value = di.read()
            return value if not di.normal_closed else not value
        else:
            raise ConfigurationError(f"unknown digital input `{label}`")

    def ai_read(self, label: str) -> float:
        """Reads the current state of the analog input specified by the given
        label.

        Raises a `ConfigurationError` exception if the analog input with the
        given label has not been added to the PLC-application before.

        Returns the read value (float).
        """
        ai = self._analog_inputs.get(label)
        if ai:
            return ai.read()
        else:
            raise ConfigurationError(f"unknown analog input `{label}`")

    def do_write(self, label: str, value: int) -> None:
        """Writes the given value (int) to the digital running with the given
        label.

        Raises a `ConfigurationError` exception if the digital running with the
        given label has not been added to the PLC-application before.
        """
        do = self._digital_outputs.get(label)
        if do:
            do.write(value)
        else:
            raise ConfigurationError(f"unknown digital running `{label}`")

    def ao_write(self, label: str, value: float) -> None:
        """Writes the given value (float) to the analog running with the given
        label.

        Raises a `ConfigurationError` exception if the analog running with the
        given label has not been added to the PLC-application before.
        """
        ao = self._analog_outputs.get(label)
        if ao:
            ao.write(value)
        else:
            raise ConfigurationError(f"unknown analog running `{label}`")

    def read_inputs(self) -> None:
        """Reads all the physical digital and analog inputs defined in the PLC
        application and writes their current states in their respective input
        registries (digital and analog input registry).

        Raises an `InternalCommunicationError` exception when a read operation
        fails.
        """
        try:
            for di in self._digital_inputs.values():
                self.di_state_registry[di.label].update(di.read())
            for ai in self._analog_inputs.values():
                self.ai_state_registry[ai.label].update(ai.read())
        except InternalCommunicationError as error:
            self.int_com_error_handler(error)

    def write_outputs(self) -> None:
        """Writes all the current states present in the digital and analog
        running registries to the corresponding physical digital and analog
        outputs.

        Raises an `InternalCommunicationError` exception when a write operation
        fails.
        """
        try:
            for do in self._digital_outputs.values():
                do.write(self.do_state_registry[do.label].curr_state)
            for ao in self._analog_outputs.values():
                ao.write(self.ao_state_registry[ao.label].curr_state)
        except InternalCommunicationError as error:
            self.int_com_error_handler(error)

    def int_com_error_handler(self, error: InternalCommunicationError):
        """Handles an `InternalCommunication` exception. An error message is
        sent to the logger. If the email notification service is used, an email
        is sent with the error message. Finally, the PLC application is
        terminated.
        """
        msg = f"program interrupted: {error.description}"
        self.logger.error(msg)
        if self.eml_notification: self.eml_notification.send(msg)
        sys.exit(msg)

    def exit_handler(self):
        """Terminates the PLC scanning loop when the user has pressed the key
        combination <Ctrl-Z> on the keyboard of the PLC (Raspberry Pi) to stop
        the PLC application.
        """
        self._exit = True

    @abstractmethod
    def control_routine(self):
        """Implements the running operation of the PLC-application.

        Must be overridden in the PLC application class derived from this class.
        """
        ...

    @abstractmethod
    def exit_routine(self):
        """Implements the routine that is called when the PLC-application is
        to be stopped, i.e. when the user has pressed the key combination
        <Ctrl-z> on the keyboard of the PLC (Raspberry Pi).

        Must be overridden in the PLC application class derived from this class.
        """
        ...

    @abstractmethod
    def emergency_routine(self):
        """Implements the routine when an `EmergencyException` has been raised.
        An `EmergencyException` can be raised anywhere within the
        `control_routine` method to signal an emergency situation for which the
        PLC application must be terminated.

        Must be overridden in the PLC application class derived from this class.
        """
        ...

    def run(self):
        """Implements the global running operation of the PLC-cycle."""
        while not self._exit:
            try:
                self.read_inputs()
                self.control_routine()
            except EmergencyException:
                self.emergency_routine()
                return
            finally:
                self.write_outputs()
        else:
            # Executed when the while condition has become False, but not when
            # the while loop has been interrupted by the `return` statement in
            # the `EmergencyException` clause
            self.exit_routine()
            self.write_outputs()
