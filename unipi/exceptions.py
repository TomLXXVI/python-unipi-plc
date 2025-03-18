import datetime
from requests.exceptions import RequestException


class InternalCommunicationError(Exception):

    def __init__(self, error: RequestException, *args):
        super().__init__(*args)
        self.description = str(error)

    def __str__(self):
        timestamp = datetime.datetime.now()
        return f"[{timestamp}] {self.description}"


class ConfigurationError(Exception):
    pass


class EmergencyException(Exception):
    pass
