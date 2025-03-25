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
        # Instantiates the base class:
        super().__init__(ip_address, port, device, eml_notification)

        # Add the inputs/outputs your PLC application needs:
        self.add_digital_input(pin='1_01', label='pushbutton1')
        self.add_digital_input(pin='1_02', label='pushbutton2')
        self.add_digital_input(pin='1_03', label='pushbutton3')
        self.add_digital_output(pin='1_01', label='lamp1')
        self.add_digital_output(pin='1_02', label='lamp2')
        self.add_digital_output(pin='1_03', label='lamp3')

    def _control_lamp(self):
        if self.di_state_registry['pushbutton1'] == 1:
            self.do_state_registry['lamp1'].update(1)

    def control_routine(self):
        self._control_lamp()

    def exit_routine(self):
        self.do_state_registry['lamp1'].update(0)
        self.logger.info('exit PLC program')

    def emergency_routine(self):
        pass


def main():
    unipi.logging.init_logger()
    os.system("clear")
    my_plc = MyPLC()
    my_plc.run()


if __name__ == '__main__':
    main()
