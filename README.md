# AWS Streamer

The AWS Streamer is a collection of video processing and streaming tools for AWS platform. It will enable users to stream from multiple camera sources, process the video stream and upload to the cloud and/or local storage. It can be used standalone, inside AWS Lambda functions, AWS ECS container or running on an AWS IoT Greengrass Core.

List of features provided by this library:

 - Streams from multiple cameras in parallel locally and to the cloud
 - Upload video streams in chunks to the S3 and/or store in the local disk
 - Upload video streams directly to Kinesis Video Streams
 - Perform ML inference on the video stream
 - Run computer vision algorithm on the video streams
 - Preview live stream in the browser

## Prerequisites

- Python 3.7 or newer.

    Tip: If your system has by default installed Python 3.6, then do the following:
    ```
    sudo ln -s /usr/bin/python3.6 /usr/bin/python3.7
    ```
    Installing Python 3.7 on top of 3.6 will break all hell loose, don't do that :)

- Install GStreamer dependencies:
    ```
    sudo apt-get update
    sudo apt-get install \
        python3-dev \
        python3-gi \
        libgirepository1.0-dev \
        gstreamer1.0-tools \
        gir1.2-gstreamer-1.0 \
        gir1.2-gst-plugins-base-1.0 \
        libgstreamer1.0-dev \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        pkg-config \
        build-essential \
        libcairo2-dev \
        libpango1.0-dev \
        libjpeg-dev \
        libgif-dev \
        librsvg2-dev \
        cmake
    ```

- Install Python dependencies
    ```
    sudo python3 -m easy_install install pip
    sudo python3 -m easy_install install virtualenv
    ```

## Install

With pip:
``` bash
pip install -v .
```

To set extra CMake flags (see below table):
``` bash
pip install -v . --install-option "build_ext" --install-option "--cmake-args=-DBUILD_KVS=ON"
```

In place:
``` bash
virtualenv venv
source venv/bin/activate

pip install --upgrade wheel pip setuptools
pip install pip==18.1
pip install --upgrade --requirement requirements.txt

./build.sh [optional:CMAKE_FLAGS]
```

| CMake flag          | Description                       | Default value |
| ------------------- | --------------------------------- | ------------- |
| -DBUILD_KVS         | Build KVS GStreamer plug-in       | OFF           |
| -DBUILD_KVS_WEBRTC  | Build KVS WebRTC binaries         | OFF           |
| -DBUILD_S3          | Build S3 GStreamer plug-in        | OFF           |
| -BUILD_GST_PYTHON   | Build GStreamer Python bindings   | OFF           |
| -BUILD_NEO_DLR      | Build SageMaker NEO runtime       | OFF           |
| -BUILD_MXNET        | Build MXnet GStreamer plug-in     | OFF           |


## Using JSON Configuration

```bash
cd examples/test_app
python3 app.py ../configs/testsrc_display.json
```

## Using AWS Streamer

``` python
import gstaws

client = gstaws.client()
```

Now you can stream from your camera to the KVS:
``` python
client.start({
    "source": {
        "name": "videotestsrc",
        "is-live": True,
        "do-timestamp": True,
        "width": 640,
        "height": 480,
        "fps": 30
    },
    "sink": {
        "name": "kvssink",
        "stream-name": "TestStream"
    }
})
```

You can also run multiple pipelines in parallel asynchronously (i.e. without waiting for the pipeline to finish):
``` python
client.schedule({
    "pipeline_0": {
        "source": {
            "name": "videotestsrc",
            "is-live": True,
            "do-timestamp": True,
            "width": 640,
            "height": 480,
            "fps": 30
        },
        "sink": {
            "name": "kvssink",
            "stream-name": "TestStream0"
        }
    },
    "pipeline_1": {
        "source": {
            "name": "videotestsrc",
            "is-live": True,
            "do-timestamp": True,
            "width": 1280,
            "height": 720,
            "fps": 30
        },
        "sink": {
            "name": "kvssink",
            "stream-name": "TestStream1"
        }
    }
})
```

To perform ML inference on the video stream:
``` python
def my_callback(metadata):
    print("Inference results: " + str(metadata))

client.start({
    "pipeline": "DeepStream",
    "source": {
        "name": "filesrc",
        "location": "/path/to/video.mp4",
        "do-timestamp": False
    },
    "nvstreammux": {
        "width": 1280,
        "height": 720,
        "batch-size": 1
    },
    "nvinfer": {
        "enabled": True,
        "config-file-path": "/path/to/nvinfer_config.txt"
    },
    "callback": my_callback
})
```

To start recording of video segments to disk:
``` python
client.schedule({
    "camera_0": {
        "pipeline": "DVR",
        "source": {
            "name": "videotestsrc",
            "is-live": True,
            "do-timestamp": True,
            "width": 640,
            "height": 480,
            "fps": 30
        },
        "sink": {
            "name": "splitmuxsink",
            "location": "/video/camera_0/output_%02d.mp4",
            "segment_duration": "00:01:00",
            "time_to_keep_days": 1
        }
    }
})
```
The command above will start recording 1-minute video segments to the given location.

To retrieve videos by timestamp, you can use the following structure:

``` python
from gstaws.utils.video import get_video_files_in_time_range, merge_video_files

file_list = get_video_files_in_time_range(
    path = "/video/camera_0/",
    timestamp_from = "2020-08-05 13:03:47",
    timestamp_to = "2020-08-05 13:05:40",
)

merged = merge_video_files(
    files = file_list,
    destination_file = "merged.mkv"
)
```

To get video frame from anywhere in the pipeline:
``` python
client.schedule({
    "camera_0": {
        "pipeline": "DVR",
        "source": {
            "name": "videotestsrc",
            "is-live": True,
            "do-timestamp": True,
            "width": 640,
            "height": 480,
            "fps": 30
        },
        "sink": {
            "name": "splitmuxsink",
            "location": "/video/camera_0/output_%02d.mp4",
            "segment_duration": "00:01:00",
            "time_to_keep_days": 1
        }
    }
})
```

## Notes

If you use AWS plug-in (e.g. KVS) outside of AWS environment (i.e. not in AWS Greengrass IoT, AWS Lambda, etc.), remember to set the following env variables:

```bash
    export AWS_ACCESS_KEY_ID=xxxxxxxxx
    export AWS_SECRET_ACCESS_KEY=xxxxxxxxxx
    export AWS_DEFAULT_REGION=ap-southeast-1 (for example)
```

## Debugging

To enable more debugging information from Gstreamer elements, set this env variable:

    export GST_DEBUG=4

More details here: https://gstreamer.freedesktop.org/documentation/tutorials/basic/debugging-tools.html?gi-language=c

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
