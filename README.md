# weewx-mqtt-input

A MQTT input driver for the [WeeWX](http://weewx.com) weather station.

This simple input driver connects to MQTT, subscribes to the
configured topics and then adds published values from MQTT to WeeWX.

Please note the following limitations (all in the name of simplicity):

* Only Python3 is supported. You need to run at least WeeWX version 4.x.
* Only a single value per MQTT topic is supported -- just the way MQTT
  is supposed to be used.
* TLS is not (yet) supported.

## Installation

For released versions of weewx-mqtt-input, use the standard WeeWX
installer like so

```bin/wee_extension --install weewx-mqtt-input.zip```

then update the WeeWX configuration and select the new driver:

```bin/wee_config --reconfigure```

Edit the `weewx.conf` file to set the address and port to point to
your MQTT broker and add your MQTT topics. Finally, restart WeeWX
(`systemctl restart weewx4.service` or similar).

Alternatively you can simply copy the weewx-mqtt-input.py file to
bin/user and configure the driver manually.

## Configuration

This input driver strives to be as simple as possible so there are
only a minimal set of things you need to configure. The mentioned
values below are the defaults. Please don't set any of the advanced
fields unless you really know you need to.

You typically want to add dozen or so topics. In many cases you only
need to supply the topic itself and the WeeWX `name` it maps to.

```
[WeewxMqttInput]
	driver = user.weewx-mqtt-input  # set weewx driver
	address = localhost             # hostname/IP of your MQTT broker
	port = 1883                     # port number for your MQTT broker
	timeout = 10                    # (advanced) MQTT connection timeout

	[[some/topic/name]]             # MQTT topic name (mandatory)
		name = weewxName        # WeeWX field to map the output to (mandatory)
		unit = US	        # unit of measurement (US/METRIC/METRICWX)
		calc_delta = False      # (advanced) measurement is a 'total' so calculate delta
		scale = 1.0             # (advanced) scale measurement by this much
		offset = 0.0            # (advanced) add this to measurement after scaling

	# repeat more topics here
```

The `calc_delta` functionality may be needed for rain
measurements. For example, my Renkforce WH2600 _dailyrainin_ should
be mapped WeeWX _rain_ with `calc_delta = True`.

`scale` and `offset` are applied after the delta calculation (if any).
The driver will report `(value * scale) + offset` to WeeWX.

That's about it. Have fun.
