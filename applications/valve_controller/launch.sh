#!/bin/bash
# launch_valve_controller.sh
# shell script to launch Python script `valve_controller.py` at startup

trap "" SIGTSTP
cd /
cd /private/python-projects/unipi || exit
source "./.unipi_env/bin/activate"
cd /
cd /private/python-projects/unipi/projects/valve_controller || exit
python valve_controller.py
deactivate
cd /
