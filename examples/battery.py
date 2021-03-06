#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`battery`
==================

Created by hbldh <henrik.blidh@nedomkull.com>
Created on 2016-04-02

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

import time

from pymetawear.client import discover_devices, MetaWearClient

print("Discovering nearby MetaWear boards...")
metawear_devices = discover_devices(timeout=2)
if len(metawear_devices) < 1:
    raise ValueError("No MetaWear boards could be detected.")
else:
    address = metawear_devices[0][0]

c = MetaWearClient(str(address), 'pygatt', debug=True)
print("New client created: {0}".format(c))


def battery_callback(data):
    """Handle a battery status tuple."""
    print("Voltage: {0}, Charge: {1}".format(
        data[0], data[1]))


print("Subscribe to battery notifications...")
c.battery.notifications(battery_callback)
time.sleep(1.0)

print("Trigger battery state notification...")
c.battery.read_battery_state()
time.sleep(1.0)

print("Unsubscribe to battery notifications...")
c.battery.notifications(None)
time.sleep(1.0)

c.disconnect()
