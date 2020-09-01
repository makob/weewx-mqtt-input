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
DRIVER_VERSION = "0.2"
POLL_INTERVAL = 1.0

log = logging.getLogger(__name__)

def loader(config_dict, engine):
    return WeewxMqttInputDriver(**config_dict[DRIVER_NAME])


class Topic():
    """MQTT topic helper class"""

    # The 'config' is assumed to be 'config_dict[topic]'
    def __init__(self, topic, config):
        self.topic = topic
        self.value = None
        self.updated = False
        self.last_total = None

        if not 'name' in config:
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

        if 'calc_delta' in config and config['calc_delta'].lower() == "true":
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

    # Read measurement and mark as not-updated.
    def read(self):
        if not self.value:
            return None

        val = float(self.value)
        self.updated = False

        if self.calc_delta:
            val = self.delta(val)
            if not val:
                return None

        return val * self.scale + self.offset

    # Pretty printer
    def __str__(self):
        return "topic={} name={} unit={} calc_delta={} scale={} offset={} last_total={}".format(
            self.topic, self.name, self.unit, self.calc_delta, self.scale, self.offset, self.last_total)

class WeewxMqttInputDriver(weewx.drivers.AbstractDevice):
    """WeeWX MQTT Input driver"""

    def __init__(self, **config_dict):
        # Get configuration
        self.address = str(config_dict.get('address', 'localhost'))
        self.port = int(config_dict.get('port', 1883))
        self.timeout = int(config_dict.get('timeout', 10))
        self.run = True
        self.topics = []

        for key in config_dict:
            # Keys with values that are sections are our topic configuration
            if type(config_dict[key]) is configobj.Section:
                topic = Topic(key, config_dict[key])
                log.debug("configured topic: {}".format(topic))
                self.topics.append(topic)

        # Spin up the MQTT client
        log.info("connecting to {}:{}...".format(self.address, self.port))
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.connect(self.address, self.port, self.timeout)
        self.client.loop_start()

    # Generator to return all updated topics of a specific unit
    def getUpdatedTopics(self, unit):
        for t in self.topics:
            if t.unit == unit and t.updated:
                yield t

    # MQTT callback for connection ack
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info("connected")
            for t in self.topics:
                client.subscribe(t.topic)
                log.info("subscribing to topic '{}' -> weewx '{}'".format(t.topic, t.name))
        elif self.run:
            log.info("connection failed ({}) - retrying...".format(rc))
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

    # WeeWX generator where we return the measurements. We iterate all
    # topics, collecting all measurements of the same unit-type. This
    # is apparently needed to get windDir working (which must go
    # together with windSpeed)
    def genLoopPackets(self):
        while True:
            for u in [weewx.US, weewx.METRIC, weewx.METRICWX]:
                found = False
                packet = {'dateTime': time.time(),
                          'usUnits':u}

                # Collect all updated topics with the same unit-type
                for t in self.getUpdatedTopics(u):
                    packet[t.name] = t.read()
                    found = True

                # Return results if any
                if found:
                    yield packet

            # avoid 100% cpu utilization :)
            time.sleep(POLL_INTERVAL)

    # WeeWX shutdown
    def closePort(self):
        self.run = False
        log.info("disconnecting from {}:{}".format(self.address, self.port))
        self.client.disconnect()
        self.client.loop_stop()

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
        Topic("testing1", { "name":"1_simple" } ),
        Topic("testing2", { "name":"2_us", "unit":"US" } ),
        Topic("testing3", { "name":"3_metric", "unit":"METRIC" } ),
        Topic("testing4", { "name":"4_metrixwx", "unit":"METRICWX" } ),
        Topic("testing5", { "name":"5_scale_offset", "scale":2.0, "offset":-0.25 } ),
        Topic("testing6", { "name":"6_calc_delta", "calc_delta":"True" } ),
    ]
    for packet in driver.genLoopPackets():
        print(weeutil.weeutil.timestamp_to_string(packet['dateTime']), packet)
