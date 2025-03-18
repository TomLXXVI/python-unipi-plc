import os
from unipi import AbstractPLC, EmailNotification
import unipi.logging


class MyPLC(AbstractPLC):

    def __init__(
        self,
        ip_address: str = "localhost",
        port: int = 8080,
        device: str | int = 1,
        eml_notification: EmailNotification | None = None
    ) -> None:
        # Instantiate the base class `AbstractPLC`:
        super().__init__(ip_address, port, device, eml_notification)

        self.add_analog_input(pin=1, label='potentiometer')

    def control_routine(self):
        value = self.ai_state_registry['potentiometer'].curr_state
        self.logger.info(f"value is {value}")

    def exit_routine(self):
        self.logger.info('exit PLC program')

    def emergency_routine(self):
        pass


def main():
    unipi.logging.init_logger(logging_level="info")
    os.system("clear")
    my_plc = MyPLC()
    my_plc.run()


if __name__ == '__main__':
    main()
