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

poll_period = 0.5


class Scale:
    path_serial = "/dev/ttyAMA0"

    def __init__(self):
        self._weight = 0.0
        self._weight_is_valid = False
        self.ecr_status = None
        self.tare_offset = 0.0

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
        self.ser.open()

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
        self.ser.reset_input_buffer()
        self.ser.write(b"Z\r")
        response = self.ecr_read()
        self.ecr_set_status(response)

    def poll(self):
        self.ser.reset_input_buffer()
        self.ser.write(b"W\r")
        response = self.ecr_read()
        if len(response) == 16:
            assert response[0:1] == b"\n"
            assert response[7:10] == b"LB\r"
            self._weight = float(response[1:7]) * 453.592
            self.ecr_set_status(response[10:16])
            self._weight_is_valid = True
        else:
            self.ecr_set_status(response)
            self._weight_is_valid = False

    def tare(self):
        self.tare_offset = self._weight;

    @property
    def display(self):
        if self._weight_is_valid:
            return ("green", "{:.0f}g".format(self._weight - self.tare_offset))
        elif self.ecr_status == b"10" or self.ecr_status == b"30": # moving
            return ("deselect", "{:.0f}g".format(self._weight - self.tare_offset))
        # elif self.ecr_status == b"20":
        #    return "-0-"
        elif self.ecr_status == b"01" or self.ecr_status == b"11":
            return ("red", "under")
        elif self.ecr_status == b"02":
            return ("red", "over")
        else:
            return ("red", "status:" + self.ecr_status.decode("utf-8"))

    @property
    def weight_is_valid(self):
        return self._weight_is_valid

    @property
    def weight(self):
        return self._weight - self.tare_offset


# For testing UI without scale present
class NoScale(Scale):
    def __init__(self):
        self._weight = 0.0
        self._weight_is_valid = True
        self.ecr_status = None
        self.tare_offset = 0.0
        return

    def poll(self):
        return

    def zero(self):
        return

    @property
    def display(self):
        return ("deselect", "no scale");


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

try:
    instrument = Scale()
except:
    instrument = NoScale()

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
        meter.set_text(instrument.display)
        #if instrument.weight_is_valid:
        #    brewcop.weight = instrument.weight
    main_loop.set_alarm_in(poll_period, poll_scale)


def handle_input(key):
    if key == "Q" or key == "q":
        raise urwid.ExitMainLoop()


header = urwid.Columns([banner, indicator], 2)
body = urwid.Overlay(meter_box, background, "center", 50, "middle", 8)

layout = urwid.Frame(header=header, body=body)
main_loop = urwid.MainLoop(layout, palette, unhandled_input=handle_input)
main_loop.set_alarm_in(0, poll_scale)
main_loop.run()

# vim: tabstop=4 shiftwidth=4 expandtab
