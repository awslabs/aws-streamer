# Data Uploader

Receives requests over MQTT and uploads video files to S3.

## Configuration

Initial configuration is stored in [config.json](./config.json).

Can be reconfigured by sending configuration by a MQTT message with JSON content to the topic:
```
[gg-core-id]/req/data
```

## Using

User can request videos to be uploaded to S3 within a specified time range by sending a MQTT message to the topic:
```
[gg-core-id]/req/data
```
Format of the message payload: [request.json](./request.json).

Response can be observed on this topic:
```
[gg-core-id]/data/res
```

You can also configure and send a request in one go, e.g.:
```
{
    "config": {
        "dir": "/video",
        "greengrass": {
            "enabled": true,
            "topic": "Streamer-GG-Stack/data/res"
        },
        "s3": {
            "enabled": true
        }
    },
    "request": {
        "gateway_id": "",
        "camera_id": "camera_0",
        "timestamp_from": "2020-08-05 13:03:47",
        "timestamp_to": "2020-08-05 13:05:46",
        "s3_bucket": "streamer-recorded-videos",
        "s3_folder": ""
    }
}
```
