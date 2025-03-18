from .plc import MemoryVariable


class ToggleSoftSwitch:
    """Represents a virtual toggle switch in PLC memory.
    
    This can be used to make a monostable pushbutton behave like a bistable
    switch.
    """
    
    def __init__(self, push_button: MemoryVariable) -> None:
        """Creates a `ToggleSoftSwitch` object.
        
        Parameters
        ----------
        push_button:
            Memory variable that is linked to the pushbutton that toggles the 
            soft switch. The switch will be toggled on a raising edge of the 
            pushbutton, i.e., when the state of the pushbutton was low (0) in 
            the previous PLC scan cycle and is high (1) in the current PLC scan 
            cycle.
        """
        self._push_button = push_button
        self._switch = MemoryVariable(curr_state=0, prev_state=0)
    
    def _toggle(self):
        """Toggles the switch on a raising edge of the pushbutton, i.e., when 
        the state of the pushbutton was low (0) in the previous PLC scan cycle 
        and is high (1) in the current PLC scan cycle.

        Returns
        -------
        The current state of the switch.
        """
        c1 = self._push_button.curr_state != self._push_button.prev_state
        c2 = self._push_button.curr_state
        if c1 and c2:
            self._switch.update(int(not self._switch.curr_state))
        return self._switch.curr_state
    
    @property
    def curr_state(self) -> int:
        """Returns the current state of the switch (i.e. the state in the 
        current PLC scan cycle).
        """
        return self._toggle()
    
    @property
    def prev_state(self) -> int:
        """Returns the previous state of the switch (i.e. the state in the 
        previous PLC scan cycle).
        """
        self._toggle()
        return self._switch.prev_state
    