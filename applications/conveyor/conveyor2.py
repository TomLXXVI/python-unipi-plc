import os
from unipi import AbstractPLC, MemoryVariable
from unipi.timers import OffDelayTimer
from unipi.switches import ToggleSwitch
from unipi.counters import UpCounter
import unipi.logging


class ConveyorPLC(AbstractPLC):

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
        self.station_B = self.add_digital_output(2, 'station_B')
        
        # Timers & Counters
        self.timer_A = OffDelayTimer(8)
        self.timer_B = OffDelayTimer(12)
        self.item_counter = UpCounter()
        
        # Flags
        self.init_flag = True
        self.done_A = False
        self.done_B = False
        self.first_scan = True  # first PLC-scan of current machine cycle
        
        # Steps
        self.X0 = MemoryVariable(curr_state=0, prev_state=0)
        self.X1 = MemoryVariable(curr_state=0, prev_state=0)
        self.X2 = MemoryVariable(curr_state=0, prev_state=0)
        self.X3 = MemoryVariable(curr_state=0, prev_state=0)
    
    def _initiate_control(self):
        self.init_flag = False
        self.X0.activate()
        self.logger.info('machine ready')
    
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
            self.X3.activate()
        
        if self.X2.active and self.X3.active and self.done_A and self.done_B:
            self.X2.deactivate()
            self.X3.deactivate()
            self.X0.activate()
            self.logger.info('press start to run conveyor or press stop to leave')
        
        if self.X0.active and self.stop_btn.active:
            self.exit_handler()
        
    def _control_actions(self):
        if self.X0.active:
            self.timer_A.reset()
            self.timer_B.reset()
            self.done_A = False
            self.done_B = False
            self.detector_A.force(0)
            self.first_scan = True
            
        if self.X1.active:
            self.conveyor.activate()
            if self.start_btn.raising_edge:
                self.item_counter.count_up()
        
        if self.X2.active:
            self.conveyor.deactivate()
            self._do_operations_station_A()
        
        if self.X3.active:
            if self.item_counter.value > 1:
                self._do_operations_station_B()
            else:
                self.done_B = True
                if self.first_scan:
                    self.logger.info('no product at station B')
                    self.first_scan = False
    
    def _do_operations_station_A(self):
        if self.timer_A.running:
            self.station_A.activate()
            if self.station_A.raising_edge:
                self.logger.info('do operations in station A')
        else:
            self.station_A.deactivate()
            self.done_A = True
            if self.station_A.falling_edge:
                self.logger.info('station A done')
    
    def _do_operations_station_B(self):
        if self.timer_B.running:
            self.station_B.activate()
            if self.station_B.raising_edge:
                self.logger.info('do operations in station B')
        else:
            self.station_B.deactivate()
            self.done_B = True
            if self.station_B.falling_edge:
                self.logger.info('station B done')
    
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
