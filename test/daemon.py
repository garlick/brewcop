#!/usr/bin/env python3

import os
import time
from enum import Enum, auto
from pathlib import PosixPath
import argparse
import subprocess
from collections import deque, namedtuple

def get_current_weight():
    query_cmd = [str(args.query_exe.resolve())]
    if args.query_exe.name == "fake-query.py":
        query_cmd.extend(['-p', str(args.pot), '-w', str(args.water), '-t', str(args.tolerance)])
    return float(subprocess.check_output(query_cmd))

class ScaleStates(Enum):
    NOPOT = "no pot"
    EMPTYPOT = "empty pot"
    COFFEEPOT = "pot with coffee"
    OVERWEIGHT = "overweight"
    ERROR = "error"

def pounds_to_fl_ounces(pounds):
    return pounds * 15.34

class Reading():
    def __init__(self, weight):
        self.weight = weight

    @property
    def state(self):
        if self.weight < args.tolerance:
            return ScaleStates.NOPOT
        if (args.pot + args.tolerance) > self.weight > (args.pot - args.tolerance):
            return ScaleStates.EMPTYPOT
        if (args.pot + args.water + args.tolerance) > self.weight > (args.pot + args.tolerance):
            return ScaleStates.COFFEEPOT
        if self.weight > (args.pot + args.water + args.tolerance):
            return ScaleStates.OVERWEIGHT
        return ScaleStates.ERROR

    @property
    def state_str(self):
        return self.state.value

    def __eq__(self, other):
        return self.state_str == other.state_str

    def __str__(self):
        if self.state in [ScaleStates.COFFEEPOT, ScaleStates.OVERWEIGHT]:
            fl_ounces = pounds_to_fl_ounces(self.weight - args.pot)
            return f'{self.state_str} ({fl_ounces:0.1f}ozs)'
        else:
            return f'{self.state_str}'

def control_loop():
    past_states = deque(maxlen=2)
    while True:
        curr_state = Reading(get_current_weight())
        past_states.appendleft(curr_state)
        if all([x == curr_state for x in past_states]):
            print(f'{curr_state}')
        else:
            print("Indeterminate state")
        time.sleep(args.interval)

def main():
    control_loop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # TODO: also support reading from stdin
    parser.add_argument('query_exe', type=PosixPath, help='path to query executable')
    parser.add_argument('-p', '--pot', type=float, default=1.6,
                        help="weight (in lbs) of the empty coffee pot")
    parser.add_argument('-w', '--water', type=float, default=2.6,
                        help="maximum amount of water (or coffee) that the pot can hold (in lbs)")
    parser.add_argument('-t', '--tolerance', type=float, default=0.02,
                        help="error tolerance (in lbs)")
    parser.add_argument('-i', '--interval', type=float, default=2,
                        help="monitor weight every X seconds")
    args = parser.parse_args()

    main()
