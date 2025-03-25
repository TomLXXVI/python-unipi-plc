from abc import ABC, abstractmethod
import requests
from .exceptions import InternalCommunicationError


class GPIO(ABC):
    """
    Represents a single (general purpose) input or running on the Unipi 1.1
    PLC-board. Class `GPIO` is an abstract class from which concrete types of
    inputs and outputs are derived (see below).

    Unipi's Evok 3 REST API is used to read and write the state of the physical
    inputs and outputs on the PLC-board.

    The class has three class attributes:
    -   `base_url`: 
            The base-URL to reach the Evok 3 REST API. It will be set when the 
            class `AbstractPLC` is instantiated (see module `plc.py`). The
            user doesn't need to access this attribute directly.
    -   `device`:
            Name of the Unipi device specified in the EVOK configuration file  
            (see: `/etc/evok/autogen.yaml`).
    -   `timeout`: 
            Sets the maximum allowable time in which a response must be
            returned after a read or write request to the Evok API. The default
            value is set to 0.5 seconds.
    """
    base_url: str
    device: str | int
    timeout: float = 0.5

    def __init__(
        self,
        pin: str | int,
        label: str, 
        normal_closed: bool = False
    ) -> None:
        """Creates a `GPIO` object.

        Parameters
        ----------
        pin:
            Sequence number of pin (based on `count` parameter in file 
            `/etc/evok/hw_definitions/UNIPI11.yaml`).
        label:
            Meaningful name that clarifies the purpose of the input or running
            pin.
        normal_closed:
            Indicates if the contact is normally closed in its resting state.
            The default is `False` (i.e. normally open).
        """
        if isinstance(pin, int) and pin < 10:
            self.pin_ID = f"{self.device}_0{pin}"
        else:
            self.pin_ID = f"{self.device}_{pin}"
        self.label = label
        self.normal_closed = normal_closed
        self._url = self._set_url()

    @abstractmethod
    def _set_url(self) -> str:
        ...

    def read(self) -> int | float:
        """Reads the current state of the input or running. If no response is
        returned before `timeout` has elapsed, an `InternalCommunicationError` 
        exception is raised.
        """
        try:
            response = requests.request(
                "GET", self._url,
                data={},
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise InternalCommunicationError(err)
        else:
            d = response.json()
            return d["value"]

    def write(self, value: int | float):
        """Writes the given value to the running. The value type can be an
        integer or a float. If no response is returned before `timeout` has
        elapsed, an exception `InterCommunicationError` is raised.
        """
        payload = {"value": value}
        try:
            response = requests.request(
                "POST", self._url,
                data=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise InternalCommunicationError(err)


class DigitalInput(GPIO):
    """
    Represents a digital input.
    """
    def _set_url(self) -> str:
        return self.base_url + f"di/{self.pin_ID}"


class DigitalOutput(GPIO):
    """
    Represents a digital running.
    """
    def _set_url(self) -> str:
        
        return self.base_url + f"ro/{self.pin_ID}"


class AnalogInput(GPIO):
    """
    Represents an analog input.
    """
    def _set_url(self) -> str:
        return self.base_url + f"ai/{self.pin_ID}"


class AnalogOutput(GPIO):
    """
    Represents an analog running.
    """
    def _set_url(self) -> str:
        return self.base_url + f"ao/{self.pin_ID}"
