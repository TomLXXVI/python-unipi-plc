import os
from unipi import AbstractPLC, EmailNotification, MemoryVariable
import unipi.logging
from unipi.exceptions import EmergencyException
from unipi.timers import SingleScanTimer
from unipi.switches import ToggleSwitch


class DcMotorPLC(AbstractPLC):
    """
    Turn a motor ON/OFF with a start, stop and emergency button. When the
    emergency button is pressed, the motor is stopped and a flashing light warns
    about the emergency until the emergency button is pressed again.
    """
    def __init__(
        self,
        ip_address: str = 'localhost',
        port: int = 8080,
        device: str | int = 1,
        email_notification: EmailNotification | None = None
    ) -> None:
        super().__init__(ip_address, port, device, email_notification)
        
        # Inputs and outputs of the application
        self.start_btn = self.add_digital_input(1, 'start')
        self.stop_btn = self.add_digital_input(2, 'stop')
        E_stop_btn = self.add_digital_input(3, 'emergency')
        self.motor = self.add_digital_output(5, 'motor')
        self.lamp = self.add_digital_output(1, 'lamp')
        
        # A monostable pushbutton is used for the E-stopbutton. However, a
        # real E-stopbutton should act like a bistable switch. The E-stopswitch 
        # is implemented here as a soft switch which is linked to the state of 
        # the actual pushbutton. The E-stopswitch will be toggled on each 
        # raising edge of the pushbutton.
        self.E_stop_switch = ToggleSwitch(E_stop_btn)
        
        # Flags
        self.init_flag = True

        # Steps
        self.step0 = MemoryVariable(curr_state=0, prev_state=0)
        self.step1 = MemoryVariable(curr_state=0, prev_state=0)
        self.step2 = MemoryVariable(curr_state=0, prev_state=0)
    
    def _initiate_control(self):
        """Initiates the control only in the first scan cycle after the PLC
        program has been started. It sets the initial step (step 0) active
        only during the first scan of the PLC program.
        """
        self.init_flag = False
        # By setting `self.init_flag` to False, the `self.init_flag` check in
        # the main control routine will return `False` in all subsequent scan 
        # cycles.
        self.step0.update(1)
        if not self.step0.prev_state:
            self.logger.info("PLC is ready to start")

    def _control_sequence(self):
        # Transition step 0 --> step 1:
        # Turn motor ON when startbutton has been pressed.
        if self.step0.curr_state and self.start_btn.curr_state == 1:
            self.step0.update(0)
            self.step1.update(1)
            if not self.step1.prev_state:
                self.logger.info("Turn motor ON")
        
        # Transition step 1 --> step 2:
        # Turn motor OFF when stopbutton has been pressed.
        if self.step1.curr_state and self.stop_btn.curr_state == 1:
            self.step1.update(0)
            self.step2.update(1)
            if not self.step2.prev_state:
                self.logger.info("Turn motor OFF")
        
        # Transition step 2 --> step 1:
        # Turn motor back ON when startbutton has been pressed again.
        if self.step2.curr_state and self.start_btn.curr_state == 1:
            self.step2.update(0)
            self.step1.update(1)
            if not self.step1.prev_state:
                self.logger.info("Turn motor ON")
    
    def _execute_actions(self):
        """Executes the actions connected to the active step determined in the
        sequence control.
        """
        # while step 1 is active, turn the motor ON
        if self.step1.curr_state:
            self.motor.update(1)
            if not self.motor.prev_state:
                self.logger.info("...motor turned ON")

        # while step 2 is active, turn the motor OFF
        if self.step2.curr_state:
            self.motor.update(0)
            if self.motor.prev_state:
                self.logger.info("...motor turned OFF")
    
    def control_routine(self):
        """Implements the PLC logic that is sequentially executed in the
        PLC scanning loop.
        """
        # Initiate the PLC scanning cycle (only at startup):
        if self.init_flag is True: self._initiate_control()
        
        # On each PLC scan, update the state of the E-stop switch and check the 
        # current state of the E-stop switch:
        self.E_stop_switch.update()
        if self.E_stop_switch.curr_state:
            raise EmergencyException

        # Determine the active step in the sequence:
        self._control_sequence()
        # Execute the actions connected to the active step:
        self._execute_actions()
    
    def exit_routine(self):
        """Routine that gets called when the user presses <Ctrl-Z>. Allows the
        system to be brought to a safe, final state before the PLC program is
        terminated.
        """
        self.motor.update(0)
        self.logger.info('exit PLC program')
    
    def emergency_routine(self):
        """Routine that gets called when an `EmergencyException` has been
        raised inside `control_routine()`.
        
        In this implementation of the emergency routine, the motor is 
        immediately turned OFF when the E-stop switch has been activated. 
        A flashing light gives a visible warning until the E-stop switch has
        been deactivated.
        
        Notes
        -----
        When an `EmergencyException` is raised from the normal PLC control 
        routine, the PLC scanning cycle (a while-loop) is interrupted by the
        emergency routine. If inside the emergency routine a sequential control
        procedure is needed, we need to implement its own PLC scanning cycle.
        """
        self.logger.info('motor emergency stop')
        self.motor.update(0)   # turn motor OFF
        self.lamp.update(1)    # turn flashlight ON
        timer_ON = SingleScanTimer(2)    # timer for the time the flashlight is ON
        timer_OFF = SingleScanTimer(2)   # timer for the time the flashlight is OFF
        emergency_flag = True  
        while emergency_flag:
            # Read the state of all physical inputs to the input registries of 
            # the PLC and update the state of the E-stop soft-switch.
            self.read_inputs()
            self.E_stop_switch.update()
            # Control logic:
            # Note: The control logic reads from the input registries and
            # writes to the running registries. It never reads a physical input 
            # directly or writes directly to a physical running. 
            if self.lamp.curr_state == 1 and timer_ON.has_elapsed:
                self.lamp.update(0)
            if self.lamp.curr_state == 0 and timer_OFF.has_elapsed:
                self.lamp.update(1)
            if not self.E_stop_switch.curr_state:
                emergency_flag = False
                self.lamp.update(0)
            # Write the state of all outputs from the running registries of the
            # PLC to the physical outputs of the PLC.
            self.write_outputs()


def main():
    # Initiates the unipi root logger:
    unipi.logging.init_logger()

    # Clear the screen:
    os.system("clear")

    # Create an instance of the PLC application and start the PLC scanning cycle.
    plc = DcMotorPLC()
    plc.run()


if __name__ == '__main__':
    main()
