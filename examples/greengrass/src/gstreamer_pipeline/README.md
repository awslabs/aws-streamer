# GStreamer Pipeline

This is a long-lived lambda that performs the following actions:

 - Streams from multiple IP cameras in parallel using RTSP protocol
 - Saves videos in chunks to the local disk

## Configuration

Default configuration is stored in [stream_config.py](./stream_config.json)

Initial configuration is stored in [config.json](./config.json).

Example configurations are in `configs` folder.

Can be reconfigured by sending configuration by a MQTT message with JSON content to the topic:
```
[gg-core-id]/config/camera
```

## Using

To run locally:
```
python3 stream_app.py [optional:CONFIG_FILE]
```

e.g.:

```
python3 stream_app.py ./configs/testsrc_display.json
```

Camera modes and configuration can be changed as instructed above.

To see the log, subscribe to this topic:
```
[gg-core-id]/camera/feed
```
