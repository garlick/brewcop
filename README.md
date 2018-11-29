### BREWCOP

**B**REWCOP is a **R**aspberry pi that **E**lectronically **W**eighs **CO**ffee **P**ots

There's a Hackathon project to put a point-of-sale scale by the
coffee pot at work, and use the weight to infer how much
coffee is in the pot, then send slack notifications to people
as it gets filled/emptied.

Right now there is a primitive C program for querying the
[Avery-Berkel 6702 bench scale](http://www.scaleservice.net/manuals/NCI/Scale%20Manual%206700SERVC.pdf)

The scale is interfaced to a raspberry pi 2 using an
[RS-232 converter](https://www.amazon.com/gp/product/B00OPU2QJ4).
The device appears as `/dev/ttyAMA0` on the pi, after disabling
console output in `raspi-config`.  No NULL modem adapter was
required between the converter and the scale, which expects a
serial configuration of 9600,7N1.

The raspberry pi has a [Touch Screen](https://www.raspberrypi.org/products/raspberry-pi-touch-display/).
