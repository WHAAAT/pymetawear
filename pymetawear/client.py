#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`client`
==================

.. moduleauthor:: hbldh <henrik.blidh@nedomkull.com>
Created on 2016-03-30

"""

from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import absolute_import

import os

import time
import subprocess
import signal
import copy

from ctypes import cdll, byref, cast, POINTER, c_uint, c_float, c_ubyte

from pymetawear.exceptions import *
from pymetawear.mbientlab.metawear.core import BtleConnection, FnGattCharPtr, FnGattCharPtrByteArray, \
    FnVoid, DataTypeId, CartesianFloat, BatteryState, Tcs34725ColorAdc, FnDataPtr
from pymetawear.specs import *

if os.environ.get('METAWEAR_LIB_SO_NAME') is not None:
    libmetawear = cdll.LoadLibrary(os.environ["METAWEAR_LIB_SO_NAME"])
else:
    libmetawear = cdll.LoadLibrary(
        os.path.join(os.path.abspath(os.path.dirname(__file__)), 'libmetawear.so'))

try:
    # Python 2
    range_ = xrange
except NameError:
    # Python 3
    range_ = range


def discover_devices(timeout=5, only_metawear=True):
    """Discover Bluetooth Devices nearby.

    Using hcitool in subprocess, since DiscoveryService in pybluez/gattlib requires sudo,
    and hcitool can be allowed to do scan without elevated permission:

        $ sudo apt-get install libcap2-bin

    installs linux capabilities manipulation tools.

        $ sudo setcap 'cap_net_raw,cap_net_admin+eip' `which hcitool`

    sets the missing capabilities on the executable quite like the setuid bit.

    References:

    SE, hcitool without sudo:
    https://unix.stackexchange.com/questions/96106/bluetooth-le-scan-as-non-root
    SE, hcitool lescan with timeout.
    https://stackoverflow.com/questions/26874829/hcitool-lescan-will-not-print-in-real-time-to-a-file

    :param int timeout: Duration of scanning.
    :param bool only_metawear: If only addresses with the string 'metawear' in its name should be returned.
    :return: List of tuples with `(address, name)`.
    :rtype: list

    """
    p = subprocess.Popen(["hcitool", "lescan"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(timeout)
    os.kill(p.pid, signal.SIGINT)
    out, err = p.communicate()
    if len(out) == 0 and len(err) > 0:
        if err == b'Set scan parameters failed: Operation not permitted\n':
            raise PyMetaWearException("Missing capabilites for hcitool!")
        if err == b'Set scan parameters failed: Input/output error\n':
            raise PyMetaWearException("Could not perform scan.")
    ble_devices = list(set([tuple(x.split(' ')) for x in filter(None, out.decode('utf8').split('\n')[1:])]))
    if only_metawear:
        return list(filter(lambda x: 'metawear' in x[1].lower(), ble_devices))
    else:
        return ble_devices


class MetaWearClient(object):
    """MetaWear client bridging the gap between `libmetawear` and a GATT communication client."""

    def __init__(self, address, debug=False):

        self._address = address
        self._debug = debug
        self._initialized = False
        self._callbacks = []

        self.initialized_fcn = FnVoid(self._initialized_fcn)
        self.sensor_data_handler = FnDataPtr(self._sensor_data_handler)

        self._btle_connection = BtleConnection(write_gatt_char=FnGattCharPtrByteArray(self._write_gatt_char),
                                               read_gatt_char=FnGattCharPtr(self._read_gatt_char))

        self.board = libmetawear.mbl_mw_metawearboard_create(byref(self._btle_connection))
        libmetawear.mbl_mw_metawearboard_initialize(self.board, self.initialized_fcn)

        if self._debug:
            print("Waiting for MetaWear board to be fully initialized...")

        while not (libmetawear.mbl_mw_metawearboard_is_initialized(self.board) and self._initialized):
            time.sleep(0.1)

    def __str__(self):
        return "MetaWearClient, {0}".format(self._address)

    def __repr__(self):
        return "<MetaWearClient, {0}>".format(self._address)

    @property
    def requester(self):
        """Property handling `GattRequester` and its connection.

        :return: The connected GattRequester instance.
        :rtype: :class:`bluetooth.ble.GATTRequester`

        """
        raise NotImplementedError("Use MetaWearClientPyGattLib or MetaWearClientPyGatt classes instead!")

    # Callback methods

    def _initialized_fcn(self):
        if self._debug:
            print("{0} initialized.".format(self))
        self._initialized = True

    def _handle_notification(self, handle, value):
        if handle == self.get_handle(METAWEAR_SERVICE_NOTIFY_CHAR[1]):
            sb = self._notify_response_to_buffer(value)
            libmetawear.mbl_mw_connection_notify_char_changed(self.board, sb.raw, len(sb.raw))
        else:
            for callback in self._callbacks:
                callback(handle, value)

    def _read_gatt_char(self, characteristic):
        """Read the desired data from the MetaWear board.

        :param pymetawear.mbientlab.metawear.core.GattCharacteristic characteristic: :class:`ctypes.POINTER`
            to a GattCharacteristic.

        """
        raise NotImplementedError("Use MetaWearClientPyGattLib or MetaWearClientPyGatt classes instead!")

    def _write_gatt_char(self, characteristic, command, length):
        """Write the desired data to the MetaWear board.

        :param pymetawear.mbientlab.metawear.core.GattCharacteristic characteristic:
        :param POINTER command: The command to send, as a byte array pointer.
        :param int length: Length of the array that command points.

        """
        raise NotImplementedError("Use MetaWearClientPyGattLib or MetaWearClientPyGatt classes instead!")

    def _sensor_data_handler(self, data):
        if (data.contents.type_id == DataTypeId.UINT32):
            data_ptr = cast(data.contents.value, POINTER(c_uint))
            return data_ptr.contents.value
        elif (data.contents.type_id == DataTypeId.FLOAT):
            data_ptr = cast(data.contents.value, POINTER(c_float))
            return data_ptr.contents.value
        elif (data.contents.type_id == DataTypeId.CARTESIAN_FLOAT):
            data_ptr = cast(data.contents.value, POINTER(CartesianFloat))
            return copy.deepcopy(data_ptr.contents)
        elif (data.contents.type_id == DataTypeId.BATTERY_STATE):
            data_ptr = cast(data.contents.value, POINTER(BatteryState))
            return copy.deepcopy(data_ptr.contents)
        elif (data.contents.type_id == DataTypeId.BYTE_ARRAY):
            data_ptr = cast(data.contents.value, POINTER(c_ubyte * data.contents.length))
            data_byte_array = []
            for i in range(0, data.contents.length):
                data_byte_array.append(data_ptr.contents[i])
            return data_byte_array
        elif (data.contents.type_id == DataTypeId.TCS34725_ADC):
            data_ptr = cast(data.contents.value, POINTER(Tcs34725ColorAdc))
            return copy.deepcopy(data_ptr.contents)

        else:
            raise RuntimeError('Unrecognized data type id: ' + str(data.contents.type_id))

    # Helper methods

    def get_handle(self, uuid):
        raise NotImplementedError("Use MetaWearClientPyGattLib or MetaWearClientPyGatt classes instead!")

    @staticmethod
    def _characteristic_2_uuids(characteristic):
        return (uuid.UUID(int=(characteristic.service_uuid_high << 64) + characteristic.service_uuid_low),
                uuid.UUID(int=(characteristic.uuid_high << 64) + characteristic.uuid_low))

    @staticmethod
    def _command_to_str(command, length):
        raise NotImplementedError("Use MetaWearClientPyGattLib or MetaWearClientPyGatt classes instead!")

    @staticmethod
    def _read_response_to_buffer(response):
        raise NotImplementedError("Use MetaWearClientPyGattLib or MetaWearClientPyGatt classes instead!")

    @staticmethod
    def _notify_response_to_buffer(response):
        raise NotImplementedError("Use MetaWearClientPyGattLib or MetaWearClientPyGatt classes instead!")
