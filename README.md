# weewx-mqtt-input
MQTT input driver for the WeeWX weather station.

This simple input driver connects to MQTT, subscribes to the
configured topics and then pushes any published values to WeeWX.

Note: Only Python3 is supported, so you need to run at least WeeWX version 4.x.

## Installation

Use the standard WeeWX installer like so

```bin/wee_extension --install=weewx-mqtt-input.zip```

Update the WeeWX configuration and select the new driver:

```bin/wee_config --reconfigure```

Add your configured topics to the `weewc.conf` file and finally
restart WeeWX (`systemctl retart weewx.service` or similar).

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
	poll = 1                        # (advanced) MQTT poll timeout

	[[the/topc/name]]               # MQTT topic name (mandatory)
		name = weewxName        # WeeWX field we map the output to (mandatory)
		unit = US	        # unit of measurement (US/METRIC/METRICWX)
		calc_delta = True       # (advanced) measurement is a 'total' so calculate delta
		scale = 1.0             # (advanced) scale measurement by this much
		offset = 0.0            # (advanced) add this to measurement after scaling

	# repeat more topics here
```

The `calc_delta` functionality may be needed for rain
measurements. For example, my Renkforce WH2600 _dailyrainin_ should
be mapped WeeWx _rain_ with `calc_delta = True`.

`scale` and `offset` are applied after the delta calculation (if any).
The driver will report `(value * scale) + offset` to WeeWX.

That's about it. Have fun.
