### coffeepot

Not much to see here.

There's a vague plan to put a point-of-sale scale by the
coffee pot at work, and use the weight to infer how much
coffee is in the pot, then send slack notifications to people
as it gets filled/emptied.

Right now there is a primitive C program for querying the
[Avery-Berkel 6702 bench scale](http://www.scaleservice.net/manuals/NCI/Scale%20Manual%206700SERVC.pdf)
bench scale.

The scale is interfaced to a raspberry pi with a touch screen,
using an [RS-232 converter](https://www.amazon.com/gp/product/B00OPU2QJ4).
Fun things could happen happen!
