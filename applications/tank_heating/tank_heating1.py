import os
from unipi import AbstractPLC, EmailNotification, MemoryVariable
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

        # Add the system inputs and outputs needed by the PLC application:
        self.add_digital_input(pin=1, label='start')
        self.add_digital_input(pin=2, label='full')
        self.add_digital_input(pin=3, label='temp_ok')
        self.add_digital_input(pin=4, label='empty')

        self.add_digital_output(pin=1, label='filling')
        self.add_digital_output(pin=2, label='heating')
        self.add_digital_output(pin=3, label='emptying')

        # Transitions
        self.start = self.di_state_registry['start']
        self.tank_full = self.di_state_registry['full']
        self.temp_ok = self.di_state_registry['temp_ok']
        self.tank_empty = self.di_state_registry['empty']

        # Actions
        self.filling = self.do_state_registry['filling']
        self.heating = self.do_state_registry['heating']
        self.emptying = self.do_state_registry['emptying']

        # Steps
        self.init_flag = True
        self.step0 = MemoryVariable(curr_state=False, prev_state=False)
        self.step1 = MemoryVariable(curr_state=False, prev_state=False)
        self.step2 = MemoryVariable(curr_state=False, prev_state=False)
        self.step3 = MemoryVariable(curr_state=False, prev_state=False)
        self.step4 = MemoryVariable(curr_state=False, prev_state=False)

    def _init_control(self):
        if self.init_flag is True:
            self.init_flag = False
            self.step0.update(True)
            if self.step0.prev_state is False:
                self.logger.info("PLC is ready to start")

    def _sequence_control(self):
        if self.step0.curr_state is True and self.start.curr_state == 1:
            self.step0.update(False)
            self.step1.update(True)
            if self.step1.prev_state is False:
                self.logger.info("step 1 -filling- is active")

        if self.step1.curr_state is True and self.tank_full.curr_state == 1:
            self.step1.update(False)
            self.step2.update(True)
            if self.step2.prev_state is False:
                self.logger.info("step 2 -heating- is active")

        if self.step2.curr_state is True and self.temp_ok.curr_state == 1:
            self.step2.update(False)
            self.step3.update(True)
            if self.step3.prev_state is False:
                self.logger.info("step 3 -emptying- is active")

        if self.step3.curr_state is True and self.tank_empty.curr_state == 1:
            self.step3.update(False)
            self.step4.update(True)
            if self.step4.prev_state is False:
                self.logger.info("step 4 -waiting- is active")
                self.logger.info("...press startbutton for the next cycle")

        if self.step4.curr_state is True and self.start.curr_state == 1:
            self.step4.update(False)
            self.step1.update(True)
            if self.step1.prev_state is False:
                self.logger.info("step 1 -filling- is active")

    def _execute_actions(self):
        # fill the tank while step 1 is active
        if self.step1.curr_state is True:
            self.filling.update(1)
            if self.filling.prev_state == 0:
                self.logger.info("...filling the tank")
        else:
            self.filling.update(0)

        # heat the liquid while step 2 is active
        if self.step2.curr_state is True:
            self.heating.update(1)
            if self.heating.prev_state == 0:
                self.logger.info("...heating the liquid")
        else:
            self.heating.update(0)

        # empty the tank while step 3 is active
        if self.step3.curr_state is True:
            self.emptying.update(1)
            if self.emptying.prev_state == 0:
                self.logger.info("...emptying the tank")
        else:
            self.emptying.update(0)

    def control_routine(self):
        self._init_control()
        self._sequence_control()
        self._execute_actions()

    def exit_routine(self):
        self.logger.info("exit PLC program")

        # turn off filling
        if self.filling.curr_state == 1:
            self.filling.update(0)
            self.logger.info("...turned off filling the tank")

        # turn off heating
        if self.heating.curr_state == 1:
            self.heating.update(0)
            self.logger.info("...turned off heating the liquid")

        # turn on emptying the tank, should tank not be empty
        if self.tank_empty.curr_state == 0:
            self.emptying.update(1)
            self.logger.info("...emptying the tank")
            # wait until the tank is empty
            while not self.tank_empty.curr_state == 1:
                self.read_inputs()
                if self.tank_empty.curr_state == 1:
                    self.emptying.update(0)
                    self.logger.info("...tank is empty: turned off emptying the tank")
                    break

    def emergency_routine(self):
        pass


def main():
    unipi.logging.init_logger(logging_level="info")
    os.system("clear")
    my_plc = MyPLC()
    my_plc.run()


if __name__ == '__main__':
    main()
