# AWS Streamer

The AWS Streamer is a collection of video processing and streaming tools for AWS platform. It will enable users to stream from multiple camera sources, process the video streams and upload to the cloud and/or local storage. It can be used standalone on the edge device, inside AWS Lambda functions, AWS ECS container or running on an AWS IoT Greengrass as a Lambda.

<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#build">Build</a> •
  <a href="#usage">Usage</a> •
  <a href="#notes">Notes</a> •
  <a href="#debugging">Debugging</a> •
  <a href="#security">Security</a> •
  <a href="#license">License</a>
</p>

## Key Features

List of features provided by this library:

 - Streams from multiple cameras in parallel locally and to the cloud
 - Upload video streams in chunks to the S3 and/or store in the local disk
 - Upload video streams directly to Kinesis Video Streams
 - Perform ML inference on the video stream
 - Run computer vision algorithm on the video streams
 - Preview live stream in the browser

## Build

### Prerequisites

- Python 3.7 or newer

- Install OS packages:

    - [Ubuntu](INSTALL.md#ubuntu)
    - [MacOS](INSTALL.md#macos)
    - [Windows](INSTALL.md#windows)

### Install

- With pip:
    ``` bash
    pip install git+https://github.com/awslabs/aws-streamer.git
    ```

    or

    ``` bash
    git clone https://github.com/awslabs/aws-streamer.git
    cd aws-streamer
    pip install -v .
    ```

    To set extra CMake flags (see below table):
    ``` bash
    python3 setup.py install
    python3 setup.py build_ext --cmake-args=-DBUILD_KVS=ON
    ```

- In place:
    ``` bash
    virtualenv venv
    source venv/bin/activate

    pip install --upgrade wheel pip setuptools
    pip install --upgrade --requirement requirements.txt

    ./build.sh [optional:CMAKE_FLAGS]
    ```


### CMake Options

| CMake flag          | Description                       | Default value |
| ------------------- | --------------------------------- | ------------- |
| -DBUILD_KVS         | Build KVS GStreamer plug-in       | OFF           |
| -DBUILD_KVS_WEBRTC  | Build KVS WebRTC binaries         | OFF           |
| -BUILD_NEO_DLR      | Build SageMaker NEO runtime       | OFF           |
| -BUILD_MXNET        | Build MXnet GStreamer plug-in     | OFF           |


## Usage

### Using JSON Configuration

```bash
cd examples/test_app
python3 app.py ../configs/testsrc_display.json
```

### Demos

There are two full-blown demos available:
- [IoT (Greengrass)](examples/greengrass/README.md)
- [Serverless (Fargate)](examples/serverless/README.md)

Click on links above to read more and see detailed architecture.

### Using AWS Streamer as SDK

``` python
import awstreamer

client = awstreamer.client()
```

- To stream from your camera to the KVS:
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

- To run multiple pipelines in parallel asynchronously (i.e. without waiting for the pipeline to finish):
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

- To perform ML inference on the video stream:
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

- To start recording of video segments to disk:
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

- To get list of files within given timestamp:
    ``` python
    from awstreamer.utils.video import get_video_files_in_time_range

    file_list = get_video_files_in_time_range(
        path = "/video/camera_0/",
        timestamp_from = "2020-08-05 13:03:47",
        timestamp_to = "2020-08-05 13:05:40",
    )
    ```

- To merge video files into a single one:
    ``` python
    from awstreamer.utils.video import merge_video_files

    merged = merge_video_files(
        files = file_list,
        destination_file = "merged.mkv"
    )
    ```

- To get video frame from any point in the pipeline:
    ``` python
    def my_callback(buffer):
        '''
        This function will be called on every frame.
        Buffer is a ndarray, do with it what you like!
        '''
        print("Buffer info: %s, %s, %s" % (str(type(buffer)), str(buffer.dtype), str(buffer.shape)))

    client.start({
        "pipeline": {
            "source": "videotestsrc",
            "source_filter": "capsfilter",
            "sink": "autovideosink"
        },
        "source": {
            "is-live": True,
            "do-timestamp": True
        },
        "source_filter": {
            "caps": "video/x-raw,width=640,height=480,framerate=30/1"
        },
        "source_filter": {
            "probes": {
                "src": my_callback
            }
        }
    })
    ```
    Above code will attach the probe to the source (outbound) pad of the source_filter plug-in.

## Notes

If you use AWS plug-in (e.g. KVS) outside of AWS environment (i.e. not in AWS Greengrass IoT, AWS Lambda, etc.), remember to set the following env variables:

```bash
export AWS_ACCESS_KEY_ID=xxxxxxxxx
export AWS_SECRET_ACCESS_KEY=xxxxxxxxxx
export AWS_DEFAULT_REGION=us-east-1 (for example)
```

## Debugging

To enable more debugging information from Gstreamer elements, set this env variable:

    export GST_DEBUG=4

More details here: https://gstreamer.freedesktop.org/documentation/tutorials/basic/debugging-tools.html?gi-language=c

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
