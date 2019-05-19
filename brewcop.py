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
import serial


class Scale:
    """
    Manage the Avery-Berkel 6702-16658 bench scale in ECR mode.
    """

    path_serial = "/dev/ttyAMA0"

    def __init__(self):
        self._weight = 0.0
        self._weight_is_valid = False
        self.ecr_status = None
        self.tare_offset = 0.0

        self.ser = serial.Serial()
        self.ser.port = self.path_serial
        self.ser.baudrate = 9600
        self.ser.timeout = 0.25
        self.ser.parity = serial.PARITY_EVEN
        self.ser.bytesize = serial.SEVENBITS
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.xonxoff = False
        self.ser.rtscts = False
        self.ser.dsrdtr = False
        self.ser.open()

    def ecr_set_status(self, response):
        """Parse response and set internal ECR status"""
        assert len(response) == 6
        assert response[0:2] == b"\nS"
        assert response[4:5] == b"\r"
        self.ecr_status = response[2:4]

    def ecr_read(self):
        """Read to ECR EOT (3)"""
        message = bytearray()
        while len(message) == 0 or message[-1] != 3:
            ch = self.ser.read(size=1)
            assert len(ch) == 1  # fail on timeout
            message.append(ch[0])
        return message

    def zero(self):
        """Send ECR Zero command to the scale and read back status"""
        self.ser.reset_input_buffer()
        self.ser.write(b"Z\r")
        response = self.ecr_read()
        self.ecr_set_status(response)

    def poll(self):
        """
        Send ECR Weigh command to the scale and read back either
        weight + status, or just status.  If a valid weight is returned,
        set _weight_is_valid True and convert pounds to grams.
        """
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
        """Incorporate weight of container on scale into future measurements"""
        self.tare_offset = self._weight

    @property
    def at_zero(self):
        """
        Test if scale status indicates scale is at zero.  The zero LED
        on the scale will be lit in this case.
        """
        if self.ecr_status == b"20":
            return True
        return False

    @property
    def display(self):
        """
        Get formatted text for scale readout.
        Gray out previous value if scale is in motion.
        Show red over/under on scale range error.
        """
        if self._weight_is_valid:
            return ("green", "{:.0f}g".format(self._weight - self.tare_offset))
        elif self.ecr_status == b"10" or self.ecr_status == b"30":  # moving
            return ("deselect", "{:.0f}g".format(self._weight - self.tare_offset))
        elif self.ecr_status == b"01" or self.ecr_status == b"11":
            return ("red", "under")
        elif self.ecr_status == b"02":
            return ("red", "over")
        else:
            return ("red", "status:" + self.ecr_status.decode("utf-8"))

    @property
    def weight_is_valid(self):
        """Return True if most recent poll() returned a valid weight."""
        return self._weight_is_valid

    @property
    def weight(self):
        """Return most recently measured weight, less tare offset if any."""
        return self._weight - self.tare_offset


# For testing UI without scale present
class NoScale(Scale):
    """
    Dummy version of scale class for UI testing.
    """

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
        return ("deselect", "no scale")


class Progress_mL(urwid.ProgressBar):
    """
    Progress bar that displays mL value instead of percentage.
    It assumes range was set to (0, max capacity in mL).
    """

    def get_text(self):
        return "{:.0f} mL".format(self.current)


class Brewcop:
    """
    Main Brewcop class.
    """

    tick_period = 0.5

    """Values for Technivorm Moccamaster insulated carafe"""
    pot_tare_g = 796
    pot_capacity_g = 1250  # 1g per mL H20

    banner_msg = ("green", "B R E W C O P")
    off_msg = ("red", "Brewcop is offline. Replace pot to continue monitoring...")

    """
    Urwid color palette.
    Tuples of (Key, font color, background color)
    """
    palette = [
        ("background", "dark blue", ""),
        ("deselect", "dark gray", ""),
        ("select", "dark green", ""),
        ("green", "dark green", ""),
        ("red", "dark red", ""),
        ("pb_todo", "black", "dark red"),
        ("pb_done", "black", "dark green"),
    ]

    """
    Source: https://www.asciiart.eu/food-and-drinks/coffee-and-tea
    N.B. this one had no attribution on that site except author's initials,
    and it seems to be widely disseminated.  Public domain?
    """
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

    def __init__(self):
        try:
            self.scale = Scale()
        except:
            self.scale = NoScale()
        self._indicator = urwid.Text("", align="right")
        self._meter = urwid.BigText("", urwid.Thin6x6Font())
        self._online = False
        self.banner = urwid.Text(self.banner_msg, align="left")
        self.status = urwid.Text(self.off_msg, align="center")
        self.pbar = Progress_mL("pb_todo", "pb_done", 0, self.pot_capacity_g)
        self.background = self.init_background(self.coffee_cup)
        self.meterbody = self.init_meterbody(self._meter, self.background)
        self.header = urwid.Columns([self.banner, self._indicator], 2)
        self.layout = urwid.Frame(
            header=self.header, body=self.meterbody, footer=self.status
        )
        self.main_loop = urwid.MainLoop(
            self.layout, self.palette, unhandled_input=self.handle_input
        )

    def init_background(self, text):
        """Return the background ascii art text, properly padded and filled."""
        bg = urwid.Text(text)
        bg = urwid.AttrMap(bg, "background")
        bg = urwid.Padding(bg, align="center", width=56)
        bg = urwid.Filler(bg)
        return bg

    def init_meterbody(self, text, background):
        """Return meter overlayed on background."""
        m = urwid.AttrMap(text, "green")
        m = urwid.Padding(m, align="center", width="clip")
        m = urwid.Filler(m, "bottom", None, 7)
        m = urwid.LineBox(m)
        m = urwid.Overlay(m, background, "center", 50, "middle", 8)
        return m

    @property
    def indicator(self):
        """Get the indicator text (upper right in header)"""
        self._indicator.get_text()

    @indicator.setter
    def indicator(self, value):
        """Set the indicator text (upper right in header)"""
        self._indicator.set_text(value)

    @property
    def meter(self):
        """Get the meter text (scale reading)"""
        self._meter.get_text()

    @meter.setter
    def meter(self, value):
        """Set the meter text (scale reading)"""
        self._meter.set_text(value)

    @property
    def online(self):
        """Get online status (True or False)"""
        return self._online

    @online.setter
    def online(self, value):
        """
        Set online status (True or False).
        If online, hide the meter and show coffee progress bar.
        If offline, show the meter and replace progress bar with offline msg.
        """
        if self._online and not value:
            self._online = False
            self.layout.body = self.meterbody
            self.layout.footer = self.status
        elif not self._online and value:
            self._online = True
            self.layout.body = self.background
            self.layout.footer = self.pbar

    def handle_input(self, key):
        """
        urwid's event loop calls this function on keyboard events
        not handled by widgets.
        """
        if key == "Q" or key == "q":
            raise urwid.ExitMainLoop()

    def poll_scale(self):
        """
        Poll the current scale value.
        Pulse the indicator green so we get visual feedback if this is slow.
        The urwid event loop is stalled while this is happening.
        If it fails, leave the indicator red and set the meter value to ----.
        """
        self.indicator = ("green", "poll")
        self.main_loop.draw_screen()
        try:
            self.scale.poll()
        except:
            self.indicator = ("red", "poll")
            self.meter = "----"
        else:
            self.indicator = ""
            self.meter = self.scale.display

    def tick(self, _loop, _data):
        """
        urwid's event loop calls this function on tick_period intervals.
        Read the scale, then update the meter and the progress bar.
        Switch online mode depending on weight reading.
        """
        self.poll_scale()
        if self.scale.weight_is_valid:
            w = self.scale.weight - self.pot_tare_g
            if w < 0:
                self.online = False
            else:
                self.pbar.set_completion(w)
                self.online = True
        self.main_loop.set_alarm_in(self.tick_period, self.tick)

    def run(self):
        """Enter urwid's event loop.  Start ticker and handle input"""
        self.main_loop.set_alarm_in(0, self.tick)
        self.main_loop.run()


brewcop = Brewcop()
brewcop.run()

# vim: tabstop=4 shiftwidth=4 expandtab
