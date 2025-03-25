import os
from unipi import AbstractPLC, MemoryVariable
from unipi.timers import OffDelayTimer
from unipi.switches import ToggleSwitch
import unipi.logging


class ConveyorPLC(AbstractPLC):
    """Simulates a conveyor application.
    
    - A product is placed on the conveyor.
    - The start button is pressed.
    - The conveyor is running.
    - A detector detects that the product is present in working station A.
    - The conveyor is stopped.
    - Operations are done on the product in station A.
    - When the operations are done, the stop button is pressed.
    - When the start button is pressed again, the cycle is repeated.
    
    The execution of operations in station A is simulated with a lamp turning on.
    The time duration of the operations in station A are simulated with a timer.
    The presence detector is simulated with a push button and a soft toggle
    switch. A press on the pushbutton means a product has arrived at station A. 
    This toggles the switch ON (a product is present at station A).
    Once the operations on the product in station A are finished, the toggle
    switch is forced to OFF in the initial step of the program. Also, the timer
    is reset.     
    """
    def __init__(self):
        super().__init__()
        
        # Inputs
        self.start_btn = self.add_digital_input(1, 'start_button')
        self.stop_btn = self.add_digital_input(2, 'stop_button')
        detector_A = self.add_digital_input(3, 'detector_A')
        self.detector_A = ToggleSwitch(detector_A)
        
        # Outputs
        self.conveyor = self.add_digital_output(5, 'conveyor')
        self.station_A = self.add_digital_output(1, 'station_A')
        
        # Timers
        self.timer_A = OffDelayTimer(8)
        
        # Flags
        self.init_flag = True
                
        # Steps
        self.X0 = MemoryVariable(curr_state=0, prev_state=0)
        self.X1 = MemoryVariable(curr_state=0, prev_state=0)
        self.X2 = MemoryVariable(curr_state=0, prev_state=0)
    
    def _initiate_control(self):
        self.init_flag = False
        self.X0.activate()
        if not self.X0.prev_state: self.logger.info("machine ready")
    
    def _control_sequence(self):
        # Update soft switch(es) at beginning of the current PLC scan cycle.
        self.detector_A.update()
        
        if self.X0.active and self.start_btn.active:
            self.X0.deactivate()
            self.X1.activate()
            self.logger.info('conveyor started')
        
        if self.X1.active and self.detector_A.active:
            self.X1.deactivate()
            self.X2.activate()
            self.logger.info('do operations in station A')
        
        if self.X2.active and self.stop_btn.active:
            self.X2.deactivate()
            self.X0.activate()
            self.logger.info('press start button to run conveyor')
    
    def _control_actions(self):
        if self.X0.active:
            self.timer_A.reset()
            self.detector_A.force(0)
            
        if self.X1.active:
            self.conveyor.activate()
        
        if self.X2.active:
            self.conveyor.deactivate()
            self._do_operations_station_A()
    
    def _do_operations_station_A(self):
        if self.timer_A.running:
            self.station_A.activate()
        else:
            self.station_A.deactivate()
            if self.station_A.falling_edge:
                self.logger.info('station A done')
    
    def control_routine(self):
        if self.init_flag: self._initiate_control()
        self._control_sequence()
        self._control_actions()
    
    def exit_routine(self):
        if self.conveyor.active:
            self.conveyor.deactivate()
    
    def emergency_routine(self):
        pass


def main():
    os.system("clear")
    unipi.logging.init_logger()
    plc = ConveyorPLC()
    plc.run()


if __name__ == '__main__':
    main()
