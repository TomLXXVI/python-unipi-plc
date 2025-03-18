import time
import os
from unipi import AbstractPLC, EmailNotification, MemoryVariable
import unipi.logging


class Timer:

    def __init__(self, dt_secs: int) -> None:
        self.dt = dt_secs
        self.t_start = None

    @property
    def has_elapsed(self) -> bool:
        if self.t_start is None:
            self.t_start = time.time()
        t_curr = time.time()
        dt = t_curr - self.t_start
        if dt >= self.dt:
            self.t_start = None
            return True
        return False


class MyPLC(AbstractPLC):
    """
    The PLC application turns 3 lamps ON and OFF in a sequence. When a lamp
    is turned ON, the lamp turns OFF again after 5 seconds, and then the next
    lamp is turned ON. The sequence is started when the startbutton is pressed.
    Once the last lamp (lamp 3) in the sequence has turned off, there are two
    possibilities: if the user has pressed the stopbutton, the sequencing is
    paused until the user has pressed the startbutton again. If the stopbutton
    hasn't been pressed, the sequence is automatically repeated.
    """
    def __init__(
        self,
        ip_address: str = "localhost",
        port: int = 8080,
        device: str | int = 1,
        eml_notification: EmailNotification | None = None
    ) -> None:
        # Instantiate the base class:
        super().__init__(ip_address, port, device, eml_notification)

        # Add the inputs/outputs needed by the PLC application:
        self.add_digital_input(pin=1, label='pushbutton1')
        self.add_digital_input(pin=2, label='pushbutton2')

        self.add_digital_output(pin=1, label='lamp1')
        self.add_digital_output(pin=2, label='lamp2')
        self.add_digital_output(pin=3, label='lamp3')

        # Define easy-to-use names:
        self.start = self.di_state_registry['pushbutton1']
        self.stop = self.di_state_registry['pushbutton2']
        self.l1 = self.do_state_registry['lamp1']
        self.l2 = self.do_state_registry['lamp2']
        self.l3 = self.do_state_registry['lamp3']

        # Flags:
        self.init_flag = 1
        self.stop_flag: bool = False

        # Steps:
        self.step0 = MemoryVariable(curr_state=0, prev_state=0)
        self.step1 = MemoryVariable(curr_state=0, prev_state=0)
        self.step2 = MemoryVariable(curr_state=0, prev_state=0)
        self.step3 = MemoryVariable(curr_state=0, prev_state=0)
        self.step4 = MemoryVariable(curr_state=0, prev_state=0)

        # Timers:
        self.t1 = Timer(5)
        self.t2 = Timer(5)
        self.t3 = Timer(5)

    @staticmethod
    def _is_turned_OFF(lamp: MemoryVariable) -> bool:
        """Checks whether the state of `lamp` between two successive scans went
        from ON to OFF.
        """
        c1 = lamp.curr_state == 0
        c2 = lamp.prev_state == 1
        return c1 and c2

    def _reset_lamps(self) -> None:
        """At the end of one sequence, each lamp has been turned OFF one time.
        So, each lamp output has a current state of 0, but a previous state of 1.
        When a new sequence is repeated, it will look like each lamp has been
        just turned OFF during the previous scan, while actually they were
        already turned OFF earlier. Therefore, the previous state of each lamp
        output must be reset to 0 before a new sequence begins.
        """
        self.l1.update(0)
        self.l2.update(0)
        self.l3.update(0)

    def _initiate_control(self):
        """Initiates the control only in the first scan cycle after the PLC
        program has been started. It sets the initial step (step 0) active
        only during the first scan of the PLC program.
        """
        if self.init_flag == 1:
            self.init_flag = 0
            # By setting `self.init_flag` to 0, the if-check will return `False`
            # in all subsequent scan cycles.
            self.step0.update(1)
            if not self.step0.prev_state:
                self.logger.info("PLC is ready to start")

    def _control_sequence(self):
        # When the stopbutton has been pressed, the stop flag is raised to
        # signal that the program needs to be paused in waiting step 4 of the
        # sequence.
        if self.stop.curr_state == 1: self.stop_flag = True

        # Transition step 0 --> step 1:
        # Turn ON lamp 1 when startbutton has been pressed.
        if self.step0.curr_state and self.start.curr_state == 1:
            self.step0.update(0)
            self.step1.update(1)
            if not self.step1.prev_state:
                self.logger.info("Turn lamp 1 ON")

        # Transition step 1 --> step 2:
        # Turn ON lamp 2 when lamp 1 turns OFF.
        if self.step1.curr_state and self._is_turned_OFF(self.l1):
            self.step1.update(0)
            self.step2.update(1)
            if not self.step2.prev_state:
                self.logger.info("Turn lamp 2 ON")

        # Transition step 2 --> step 3:
        # Turn ON lamp 3 when lamp 2 turns OFF.
        if self.step2.curr_state and self._is_turned_OFF(self.l2):
            self.step2.update(0)
            self.step3.update(1)
            if not self.step3.prev_state:
                self.logger.info("Turn lamp 3 ON")

        # Transition step 3 --> step 1:
        # Repeat sequence when lamp 3 turns OFF and stopbutton has not been pressed
        if self.step3.curr_state and (self._is_turned_OFF(self.l3) and not self.stop_flag):
            self.step3.update(0)
            self.step1.update(1)
            self._reset_lamps()  # before start of new sequence: reset all lamp outputs
            if not self.step1.prev_state:
                self.logger.info("Turn lamp 1 ON")

        # Transition step 3 --> step 4:
        # Pause sequencing when lamp 3 turns OFF and stopbutton has been pressed
        if self.step3.curr_state and (self._is_turned_OFF(self.l3) and self.stop_flag):
            self.step3.update(0)
            self.step4.update(1)
            self.stop_flag = False  # reset the stop flag when step 4 becomes active
            if not self.step4.prev_state:
                self.logger.info("Pausing...")

        # Transition step 4 --> step 1:
        # Repeat the sequence when the startbutton has been pressed again.
        if self.step4.curr_state and self.start.curr_state == 1:
            self.step4.update(0)
            self.step1.update(1)
            self._reset_lamps()  # before start of new sequence: reset all lamp outputs
            if not self.step1.prev_state:
                self.logger.info("Turn lamp 1 ON")

    def _execute_actions(self):
        # While step 1 active:
        # Switch ON lamp 1; switch OFF when timer has finished.
        if self.step1.curr_state:
            if self.l1.curr_state != self.l1.prev_state:
                self.logger.info("...lamp 1 is ON")
            if not self.t1.has_elapsed:
                self.l1.update(1)
            else:
                self.l1.update(0)

        # While step 2 active:
        # Switch ON lamp 2; switch OFF when timer has finished.
        if self.step2.curr_state:
            if self.l2.curr_state != self.l2.prev_state:
                self.logger.info("...lamp 2 is ON")
            if not self.t2.has_elapsed:
                self.l2.update(1)
            else:
                self.l2.update(0)

        # While step 3 active:
        # Switch ON lamp 3; switch OFF when timer has finished.
        if self.step3.curr_state:
            if self.l3.prev_state != self.l3.curr_state:
                self.logger.info("...lamp 3 is ON")
            if not self.t3.has_elapsed:
                self.l3.update(1)
            else:
                self.l3.update(0)

    def control_routine(self):
        self._initiate_control()
        self._control_sequence()
        self._execute_actions()

    def exit_routine(self):
        # Turn OFF all the lamps.
        self.l1.update(0)
        self.l2.update(0)
        self.l3.update(0)
        self.logger.info("Exit PLC program.")

    def emergency_routine(self):
        pass


def main():
    unipi.logging.init_logger()
    os.system("clear")
    my_plc = MyPLC()
    my_plc.run()


if __name__ == '__main__':
    main()
