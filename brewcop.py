#!/usr/bin/env python3

##############################################################
#  Copyright 2019 Jim Garlick <garlick.jim@gmail.com>
#  (c.f. COPYING)
#
#  This file is part of BREWCOP, a coffee pot monitor.
#  For details, see https://github.com/garlick/brewcop.
#
#  SPDX-License-Identifier: BSD-3-Clause
##############################################################

import urwid
import subprocess
import serial

poll_period = 2


class Scale:
    path_helper = "/usr/local/bin/scale_query"
    path_serial = "/dev/ttyAMA0"

    def __init__(self):
        self._weight = 0.0
        self.ecr_status = None

        self.ser = serial.Serial()
        self.ser.port = self.path_serial
        self.ser.baudrate = 9600
        self.ser.sertimeout = 0.25
        self.ser.parity = serial.PARITY_EVEN
        self.ser.bytesize = serial.SEVENBITS
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.xonxoff = False
        self.ser.rtscts = False
        self.ser.dsrdtr = False

    def ecr_set_status(self, response):
        assert len(response) == 6
        assert response[0:2] == b"\nS"
        assert response[4:5] == b"\r"
        self.ecr_status = response[2:4]

    def ecr_read(self):
        # Read to EOT (\x03)
        message = bytearray()
        while len(message) == 0 or message[-1] != 3:
            ch = self.ser.read(size=1)
            assert len(ch) == 1  # fail on timeout
            message.append(ch[0])
        return message

    def zero(self):
        self.ser.open()
        self.ser.write(b"Z\r")
        response = self.ecr_read()
        self.ecr_set_status(response)
        self.ser.close()

    def poll(self):
        out = subprocess.Popen(
            [self.path_helper], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        stdout, stderr = out.communicate()
        self._weight = float(stdout) * 453.592

    @property
    def weight(self):
        return self._weight


# Placeholder for "application logic"
class Brewcop:
    valid_modes = ["beans", "brew", "clean"]

    def __init__(self):
        self._mode = "beans"
        self._weight = 0.0

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        if not value in self.valid_modes:
            raise ValueError("Invalid mode")
        self._mode = value

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, value):
        self._weight = value


# Tuples of (Key, font color, background color)
palette = [
    ("background", "dark blue", ""),
    ("deselect", "dark gray", ""),
    ("select", "dark green", ""),
    ("green", "dark green", ""),
    ("red", "dark red", ""),
]

# Source: https://www.asciiart.eu/food-and-drinks/coffee-and-tea
# N.B. this one had no attribution on that site except author's initials,
# and it seems to be widely disseminated.  Public domain?
coffee_cup = u'''\
                      (
                        )     (
                 ___...(-------)-....___
             .-""       )    (          ""-.
       .-'``'|-._             )         _.-|
      /  .--.|   `""---...........---""`   |
     /  /    |                             |
     |  |    |                             |
      \  \   |                             |
       `\ `\ |                             |
         `\ `|                             |
         _/ /\                             /
        (__/  \                           /
     _..---""` \                         /`""---.._
  .-'           \                       /          '-.
 :               `-.__             __.-'              :
 :                  ) ""---...---"" (                 :
  '._               `"--...___...--"`              _.'
jgs \""--..__                              __..--""/
     '._     """----.....______.....----"""     _.'
        `""--..,,_____            _____,,..--""`
                      `"""----"""`
'''

instrument = Scale()
brewcop = Brewcop()

banner = urwid.Text(("green", "B R E W C O P"), align="left")

indicator = urwid.Text("", align="right")

background = urwid.Text(coffee_cup)
background = urwid.AttrMap(background, "background")
background = urwid.Padding(background, align="center", width=56)
background = urwid.Filler(background)

meter = urwid.BigText("no scale", urwid.Thin6x6Font())
meter_box = urwid.AttrMap(meter, "green")
meter_box = urwid.Padding(meter_box, align="center", width="clip")
meter_box = urwid.Filler(meter_box, "bottom", None, 7)
meter_box = urwid.LineBox(meter_box)


def on_beans(w, state):
    if state:
        brewcop.mode = "beans"
        w.set_label(("select", w.label))
    else:
        w.set_label(("deselect", w.label))


def on_brew(w, state):
    if state:
        brewcop.mode = "brew"
        w.set_label(("select", w.label))
    else:
        w.set_label(("deselect", w.label))


def on_clean(w, state):
    if state:
        brewcop.mode = "clean"
        w.set_label(("select", w.label))
    else:
        w.set_label(("deselect", w.label))


def on_tare(w):
    try:
        instrument.zero()
    except:
        indicator.set_text(("red", "tare"))
    else:
        indicator.set_text(("green", "tare"))
        meter.set_text("{:.1f}g".format(instrument.weight))


def poll_scale(_loop, _data):
    indicator.set_text(("green", "poll"))
    main_loop.draw_screen()
    try:
        instrument.poll()
    except:
        indicator.set_text(("red", "poll"))
        meter.set_text("----")
    else:
        indicator.set_text("")
        meter.set_text("{:.1f}g".format(instrument.weight))
        brewcop.weight = instrument.weight
    main_loop.set_alarm_in(poll_period, poll_scale)


def handle_input(key):
    if key == "Q" or key == "q":
        raise urwid.ExitMainLoop()


rgroup = []

beans = urwid.RadioButton(rgroup, ("select", "Beans"), on_state_change=on_beans)
beans = urwid.LineBox(beans)

brew = urwid.RadioButton(rgroup, ("deselect", "Brew"), on_state_change=on_brew)
brew = urwid.LineBox(brew)

clean = urwid.RadioButton(rgroup, ("deselect", "Clean"), on_state_change=on_clean)
clean = urwid.LineBox(clean)

tare = urwid.Button("Tare", on_press=on_tare)
tare = urwid.LineBox(tare)

header = urwid.Columns([banner, indicator], 2)
body = urwid.Overlay(meter_box, background, "center", 50, "middle", 8)
footer = urwid.GridFlow([beans, brew, clean, tare], 14, 4, 0, "center")

layout = urwid.Frame(header=header, body=body, footer=footer)
main_loop = urwid.MainLoop(layout, palette, unhandled_input=handle_input)
main_loop.set_alarm_in(0, poll_scale)
main_loop.run()

# vim: tabstop=4 shiftwidth=4 expandtab
