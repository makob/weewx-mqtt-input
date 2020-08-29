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
# See the README.md for configuration and installation help.

import logging
import time
import weewx.drivers
import paho.mqtt.client as mqtt
import configobj

DRIVER_NAME = 'WeewxMqttInput'
DRIVER_VERSION = "0.1"

log = logging.getLogger(__name__)

def loader(config_dict, engine):
    return WeewxMqttInputDriver(**config_dict[DRIVER_NAME])

# Topic helper class
class Topic():
    # The 'config' is assumed to be 'config_dict[topic]'
    def __init__(self, topic, config):
        self.topic = topic
        self.value = None
        self.updated = False
        self.last_total = None

        if not ('name' in config):
            msg = "topic '{}' has no 'name' configured".format(topic)
            raise ValueError(msg)

        self.name = config['name']
        if ' ' in self.name or '/' in self.name:
            log.warning("weewx field name '{}' may contain invalid characters".format(self.name))

        if 'unit' in config:
            if config['unit'] == 'US':
                self.unit = weewx.US
            elif config['unit'] == 'METRIC':
                self.unit = weewx.METRIC
            elif config['unit'] == 'METRICWX':
                self.unit = weewx.METRICWX
            else:
                raise ValueError('unit must be US, METRIC or METRICWX')
        else:
            self.unit = weewx.US

        if 'calc_delta' in config:
            self.calc_delta = True
        else:
            self.calc_delta = False

        if 'scale' in config:
            self.scale = float(config['scale'])
        else:
            self.scale = 1.0

        if 'offset' in config:
            self.offset = float(config['offset'])
        else:
            self.offset = 0.0

    # Store a new measurement
    def store(self, value):
        self.updateTime = int(time.time())
        self.value = value
        self.updated = True

    # Delta calculation (and storage). Inspired by the 'interceptor' driver.
    def delta(self, new_total):
        if self.last_total is None:
            log.debug("topic '{}' value {} no last total, delta skipped".format(self.topic, new_total))
            self.last_total = new_total
            return None

        elif new_total < self.last_total:
            log.debug("topic '{}' value {} last_total {} wrap-around".format(self.topic, new_total, self.last_total))
            self.last_total = new_total
            return new_total

        else:
            delta = new_total - self.last_total
            log.debug("topic '{}' value {} last_total {} delta {}".format(self.topic, new_total, self.last_total, delta))
            self.last_total = new_total
            return delta

    # Read measurement. Returns None if not updated
    def read(self):
        if self.updated:
            val = float(self.value)
            self.updated = False

            if self.calc_delta:
                val = self.delta(val)
                if not val:
                    return None

            return val * self.scale + self.offset
        else:
            return None

    # Pretty printer
    def __str__(self):
        return "topic={} name={} unit={} calc_delta={} scale={} offset={}".format(
            self.topic, self.name, self.unit, self.calc_delta, self.scale, self.offset)

class WeewxMqttInputDriver(weewx.drivers.AbstractDevice):
    """WeeWX MQTT Input driver"""

    def __init__(self, **config_dict):
        # Get configuration
        self.address = str(config_dict.get('address', 'localhost'))
        self.port = int(config_dict.get('port', 1883))
        self.timeout = int(config_dict.get('timeout', 10))
        self.poll = int(config_dict.get('poll', 1.0))
        self.run = True

        # Keys with values that are dicts are out topic configuration
        self.topics = []
        for key in config_dict:
            if type(config_dict[key]) is configobj.Section:
                topic = Topic(key, config_dict[key])
                self.topics.append(topic)

        for t in self.topics:
            log.debug("configured topic: {}".format(t))

        # Spin up the MQTT client
        log.info("connecting to {}:{}...".format(self.address, self.port))
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.connect(self.address, self.port, self.timeout)

    # MQTT callback for connection ack
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info("connected")
            for t in self.topics:
                client.subscribe(t.topic)
                log.info("subscribing to topic '{}'".format(t.topic))
        elif self.run:
            log.info("connection failure code {} - retrying...".format(rc))
            self.client.connect(self.address, self.port, self.timeout)

    # MQTT callback for message publish
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        value = msg.payload.decode('ascii')

        for t in self.topics:
            if topic == t.topic:
                t.store(value)
                log.debug("topic '{}' value '{}' weewx-field '{}'".format(
                    topic, value, t.name))
                return
        log.error("unknown topic '{}' value '{}'".format(topic, value))

    # MQTT callback for disconnects
    def on_disconnect(self, client, userdata, rc):
        log.info("disconnected, result code {}".format(rc))
        if self.run:
            log.info("reconnecting to {}:{}...".format(self.address, self.port))
            self.client.connect(self.address, self.port, self.timeout)

    # WeeWX generator where we return the measurements
    def genLoopPackets(self):
        while True:
            # Scan all topics. We only send stuff if we have read new data
            for t in self.topics:
                value = t.read()
                if value:
                    packet = {'dateTime': t.updateTime,
                               'usUnits': t.unit,
                               t.name: value}
                    yield packet

            # Use PAHO's poll timeout as our delay function
            self.client.loop(self.poll)

    # WeeWX shutdown
    def closePort(self):
        self.run = False
        log.info("disconnecting from {}:{}".format(self.address, self.port))
        self.client.disconnect()

    # WeeWX name thingy
    @property
    def hardware_name(self):
        return "weewx-mqtt-input"

# To test this driver, run it directly as follows:
# PYTHONPATH=/home/weewx/bin python3 /home/weewx/bin/user/weewx-mqtt-input.py
if __name__ == "__main__":
    import weeutil.weeutil
    import weeutil.logger
    import weewx
    weewx.debug = 1
    weeutil.logger.setup('weewx-mqtt-input', {})

    driver = WeewxMqttInputDriver()
    driver.topics = [
        Topic("testing1", { "name":"map_to_this" } ),
        Topic("testing2", { "name":"anotherMappedName", "unit":"US" } ),
        Topic("testing3", { "name":"anotherMappedName", "unit":"METRIC" } ),
        Topic("testing4", { "name":"yet_another", "unit":"METRICWX" } ),
    ]
    for packet in driver.genLoopPackets():
        print(weeutil.weeutil.timestamp_to_string(packet['dateTime']), packet)
