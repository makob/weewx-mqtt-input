#!/usr/bin/python3
#
# Copyright 2020 Jakob Butler <makob@makob.dk>
#
# weewx-mqtt-input: WeeWX MQTT Input driver
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.
#
# See http://www.gnu.org/licenses/
#
# Installer for the weewx-mqtt-input MqttInput driver
# Based on the fileparse example plugin from Matthew Wall

from weecfg.extension import ExtensionInstaller

def loader():
    return WeewxMqttInputInstaller()

class WeewxMqttInputInstaller(ExtensionInstaller):
    def __init__(self):
        super(WeewxMqttInputInstaller, self).__init__(
            version="0.1",
            name='weewx-mqtt-input',
            description='WeeWX MQTT Input driver',
            author="Jakob Butler",
            author_email="makob@makob.dk",
            config={
                'Station':
                {
                    'station_type': 'WeewxMqttInput'
                },
                'WeewxMqttInput':
                {
                    'driver': 'user.weewx-mqtt-input',
                    'address': 'localhost',
                    'port':1883,
                    'some/topic/name':
                    {
                        'name':'weewx-field',
                        'unit':'US',
                        'calc_delta':'False',
                        'scale':1.0,
                        'offset':0,
                    },
                },
            },
            files=[('bin/user', ['./weewx-mqtt-input.py'])]
        )
