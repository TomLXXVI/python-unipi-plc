import os
from unipi import AbstractPLC, MemoryVariable
from unipi.counters import UpDownCounter
import unipi.logging


class CounterPLC(AbstractPLC):
    
    def __init__(self) -> None:
        super().__init__()
        
        # Inputs
        self.start_button = self.add_digital_input(1, 'start_button')
        self.count_up_button = self.add_digital_input(2, 'count_up_button')
        self.count_down_button = self.add_digital_input(3, 'count_down_button')
        self.stop_button = self.add_digital_input(4, 'stop_button')
        
        # Counter
        self.counter = UpDownCounter(preset_value=5)
        
        # Flags
        self.init_flag = True
        
        # Steps
        self.X0 = MemoryVariable(curr_state=0, prev_state=0)
        self.X1 = MemoryVariable(curr_state=0, prev_state=0)
        
    def _init_control(self):
        self.init_flag = False
        self.X0.activate()
        self.logger.info('machine ready')
    
    def _sequence_control(self):
        if self.X0.active and self.start_button.active:
            self.X0.deactivate()
            self.X1.activate()
            self.logger.info('machine running')
        
        if self.X1.active and self.stop_button.active:
            self.X1.deactivate()
            self.X0.activate()
            self.logger.info('press start to run again')
    
    def _execute_actions(self):
        if self.X0.active:
            self.counter.reset()
        
        if self.X1.active:
            c1 = self.count_up_button.raising_edge 
            c2 = self.count_down_button.raising_edge
            if c1 or c2:
                if c1:
                    self.counter.count_up()
                if c2:
                    self.counter.count_down()
                self.logger.info(f'counter value = {self.counter.value}')
                if self.counter.value == 0:
                    self.logger.info('hip hip hurray')
    
    def control_routine(self):
        if self.init_flag:
            self._init_control()
        self._sequence_control()
        self._execute_actions()
    
    def exit_routine(self):
        pass
    
    def emergency_routine(self):
        pass


def main():
    unipi.logging.init_logger()
    os.system('clear')
    counter_plc = CounterPLC()
    counter_plc.run()


if __name__ == '__main__':
    main()
