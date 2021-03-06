#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`led`
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

c = MetaWearClient(str(address), debug=True)
print("New client created: {0}".format(c))


def switch_callback(data):
    if data == 1:
        print("Switch pressed!")
    elif data == 0:
        print("Switch released!")

# Create subscription
c.switch.notifications(switch_callback)

time.sleep(10.0)

# Remove subscription
c.switch.notifications(None)
time.sleep(1.0)

c.disconnect()

