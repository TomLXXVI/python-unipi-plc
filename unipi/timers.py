import time


class Timer:

    def __init__(self, dt_secs: int) -> None:
        """Creates a `Timer` object.
        
        Parameters
        ----------
        dt_secs: int
            Time span of the timer in seconds.
        """
        self.dt = dt_secs
        self.t_start = None

    @property
    def has_elapsed(self) -> bool:
        """Returns `True` when the time span of the timer has elapsed, else
        returns `False`.
        
        When the method is called the first time, the timer is initialized with
        the current time (in seconds). On each next call, the difference between
        the current time and the initial time is taken. When the difference is
        greater than or equal to `dt_secs` specified at instantiation of the
        timer object, `True` is returned. Otherwise, `False` is returned. Also,
        when time has been elapsed (`True` is returned), the timer will be 
        automatically re-initialized on the next call. 
        """
        if self.t_start is None:
            self.t_start = time.time()
        t_curr = time.time()
        dt = t_curr - self.t_start
        if dt >= self.dt:
            self.t_start = None
            return True
        return False
