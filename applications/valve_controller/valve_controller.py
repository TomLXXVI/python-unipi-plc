import datetime
import random
import os
import unipi.logging
from decouple import config
from unipi import EmailNotification
from unipi import AbstractPLC


class ValveController(AbstractPLC):

    def __init__(
        self,
        ip_address: str = "localhost",
        port: int = 8080,
        device: str | int = 1,
        eml_notification: EmailNotification | None = None,
        update_interval: int = 5,
        voltage_range: tuple[int, int] = (0, 10)
    ) -> None:
        super().__init__(ip_address, port, device, eml_notification)

        self.add_analog_output(pin=1, label="valve_position")

        self.t_start = datetime.datetime.now()
        self.update_interval = update_interval

        self.V_low = voltage_range[0]
        self.V_high = voltage_range[1]

    def set_valve_position(self):
        t_now = datetime.datetime.now()
        if (t_now - self.t_start).seconds >= self.update_interval:
            self.t_start = t_now
            V = round(random.uniform(self.V_low, self.V_high), 1)
            self.ao_state_registry["valve_position"].curr_state = V
            valve_pos_percent = int((10 - self.ao_state_registry["valve_position"].curr_state) * 10.0)
            # Note: a value of 10 corresponds with 0 V on the analog running,
            # while a value of 0 corresponds with 10 V on the analog running.
            self.logger.info(f"current valve position = {valve_pos_percent} %")

    def control_routine(self):
        self.set_valve_position()

    def exit_routine(self):
        self.ao_state_registry["valve_position"].curr_state = self.V_high  # V_high results in 0 V on the analog running
        now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        self.logger.info('exit valve controller')
        if self.eml_notification: self.eml_notification.send(f"[{now}] exit program")

    def emergency_routine(self):
        pass


def main():

    unipi.logging.init_logger()

    os.system("clear")  # clear the screen when the app starts up

    eml_notification = EmailNotification(
        smtp_server='smtp.gmail.com',
        port=587,
        sending_address='unipi.plc@gmail.com',
        password=config('PASSWORD', default=''),
        receiving_address='tom.chr@proximus.be',
        subject="VALVE CONTROLLER"
    )

    valve_controller = ValveController(
        ip_address="localhost",
        port=8080,
        eml_notification=eml_notification,
        update_interval=1,
        voltage_range=(0, 10)
    )

    valve_controller.run()


if __name__ == '__main__':
    main()
