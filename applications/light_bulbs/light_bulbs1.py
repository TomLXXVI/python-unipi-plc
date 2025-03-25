import os

from unipi import AbstractPLC, EmailNotification, MemoryVariable
import unipi.logging


class MyPLC(AbstractPLC):
    """
    Turn a lamp ON/OFF with a single pushbutton.
    """
    def __init__(
        self,
        ip_address: str = "localhost",
        port: int = 8080,
        device: int = 1,
        eml_notification: EmailNotification | None = None
    ) -> None:
        # Instantiate the base class:
        super().__init__(ip_address, port, device, eml_notification)

        # Add the inputs/outputs needed by the PLC application:
        self.add_digital_input(pin=1, label='pushbutton')
        self.add_digital_output(pin=1, label='lamp')

        # Use descriptive names for the state variables associated with inputs 
        # and outputs:
        self.push_button = self.di_state_registry['pushbutton']
        self.lamp = self.do_state_registry['lamp']
        self.soft_switch = MemoryVariable(curr_state=0, prev_state=0)

        # Steps:
        self.init_flag = 1
        self.step0 = MemoryVariable(curr_state=0, prev_state=0)  # init-step
        self.step1 = MemoryVariable(curr_state=0, prev_state=0)  # turn lamp ON
        self.step2 = MemoryVariable(curr_state=0, prev_state=0)  # turn lamp OFF

    def toggle_switch(self) -> int:
        """Toggles the soft switch each time the push button is pressed.
        Only when the state of the pushbutton has changed between two scan
        cycles and is currently ON, the state of the soft switch is inverted.
        """
        c1 = self.push_button.curr_state != self.push_button.prev_state
        c2 = self.push_button.curr_state
        if c1 and c2:
            self.soft_switch.update(int(not self.soft_switch.curr_state))
        return self.soft_switch.curr_state

    def _initiate_control(self):
        """Initiates the control program only in the first scan cycle just after
        the startup of the PLC program. It sets the initial step (step 0) active
        only during the first scan of the PLC program.
        """
        if self.init_flag == 1:
            self.init_flag = 0
            # By setting `self.init_flag` to 0, the if-check will return `False`
            # in all subsequent scans.
            self.step0.update(1)
            if not self.step0.prev_state:
                self.logger.info("PLC is ready to start")

    def _sequential_control(self):
        """Determines which step of the sequence is active depending on the
        current state of the soft switch. This function is called on each scan 
        of the PLC program.
        """
        # At the beginning of each scan -and only then!-, the current state of
        # the soft switch must be determined. (During the execution of a single
        # scan cycle, the values of the state variables of the machine should
        # remain fixed. It is as if a snapshot is taken of the machine's state
        # variables each time a new scan cycle starts.)
        switch_state = self.toggle_switch()

        # If the initial step 0 is active (i.e. only at the very first scan
        # cycle of the program) and the state of the soft switch is ON, set
        # next step 1 -lamp ON- of the sequence active, which means a transition
        # of the machine's state from step 0 to step 1 is to be made.
        if self.step0.curr_state and switch_state == 1:
            self.step0.update(0)
            self.step1.update(1)
            if not self.step1.prev_state:
                self.logger.info("turn lamp ON")

        # If step 1 of the sequence -lamp ON- is active and the state of the
        # soft switch is OFF, set next step 2 of the sequence -lamp OFF-.
        if self.step1.curr_state and switch_state == 0:
            self.step1.update(0)
            self.step2.update(1)
            if not self.step2.prev_state:
                self.logger.info("turn lamp OFF")

        # If step 2 of the sequence -lamp OFF is active and the state of the
        # soft switch is ON, go back to step 1 of the sequence -lamp ON-.
        if self.step2.curr_state and switch_state == 1:
            self.step2.update(0)
            self.step1.update(1)
            if not self.step1.prev_state:
                self.logger.info("turn lamp ON")

    def _execute_actions(self):
        """Executes the actions connected to the active step determined in the
        sequence control.
        """
        # while step 1 is active, turn the lamp ON
        if self.step1.curr_state:
            self.lamp.update(1)
            if not self.lamp.prev_state:
                self.logger.info("...lamp turned ON")

        # while step 2 is active, turn the lamp OFF
        if self.step2.curr_state:
            self.lamp.update(0)
            if self.lamp.prev_state:
                self.logger.info("...lamp turned OFF")

    def control_routine(self):
        """Implements the PLC program that is sequentially executed in the
        PLC scanning loop.
        """
        # Initiate the PLC scanning cycle (only at startup):
        self._initiate_control()
        # Determine the active step in the sequence:
        self._sequential_control()
        # Execute the actions connected to the active step:
        self._execute_actions()

    def exit_routine(self):
        """Routine that gets called when the user presses <Ctrl-Z>. Allows the
        system to be brought to a safe, final state before the PLC program is
        terminated.
        """
        self.lamp.update(0)
        self.logger.info('exit PLC program')

    def emergency_routine(self):
        """Routine that gets called when an `EmergencyException` has been
        raised inside `control_routine()`.
        """
        pass


def main():
    # Initiates the unipi root logger:
    unipi.logging.init_logger()

    # Clear the screen:
    os.system("clear")

    # Create an instance of the PLC application and start the PLC scanning cycle.
    my_plc = MyPLC()
    my_plc.run()


if __name__ == '__main__':
    main()
