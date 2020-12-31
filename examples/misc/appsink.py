'''
Following example shows how to use appsink and appsrc
'''

import os
import awstreamer
from pprint import pformat
from time import sleep
import datetime
import numpy as np

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib  # noqa:F401,F402

dir_path = os.path.abspath(os.path.dirname(__file__))

def on_new_sample(sink, src):
    '''
    This function will be called on every frame coming to the appsink.
    At the end, processed frame is pushed to appsrc in another pipeline
    '''
    sample = sink.emit("pull-sample")
    buffer = sample.get_buffer()
    caps = sample.get_caps()
    height = caps.get_structure(0).get_value('height')
    width = caps.get_structure(0).get_value('width')
    mem = buffer.get_all_memory()
    success, arr = mem.map(Gst.MapFlags.READ)
    img = np.ndarray((height,width,3),buffer=arr.data,dtype=np.uint8)
    print(img.shape)

    # Simulate slow processing with sleep
    sleep(0.1)
    print(datetime.datetime.now())

    # Push to appsrc
    src.emit("push-buffer", Gst.Buffer.new_wrapped(img.tobytes()))
    mem.unmap(arr)
    return Gst.FlowReturn.OK


if __name__ == '__main__':

    # Initialize awstreamer client
    client = awstreamer.client()

    # App source pipeline
    pipeline = client.add({
        "pipeline": {
            "source": "appsrc",
            "source_filter": "capsfilter",
            "convert": "videoconvert",
            "sink": "autovideosink"
        },
        "source": {
            "name": "source",
            "emit-signals": True,
            "do-timestamp": True,
            "is-live": True,
            "block": True
        },
        "source_filter": {
            "caps": "video/x-raw,format=RGB,width=320,height=320,framerate=30/1,interlace-mode=(string)progressive"
        },
        "sink": {
            "sync": False
        },
        "timeout": 5
    })

    # App sink pipeline
    client.add({
        "pipeline": {
            "source": "videotestsrc",
            "source_filter": "capsfilter",
            "timeoverlay": "timeoverlay",
            "tee": "tee",
            "buffer": "queue",
            "convert": "videoconvert",
            "convert_filter": "capsfilter",
            "encoder": "x264enc",
            "encoder_filter": "capsfilter",
            "mux": "qtmux",
            "sink": "filesink",
            "queue": "queue",
            "scale": "videoscale",
            "scale_filter": "capsfilter",
            "appsink": "appsink"
        },
        "source": {
            "is-live": True,
            "do-timestamp": True
        },
        "source_filter": {
            "caps": "video/x-raw,format=RGB,width=640,height=480,framerate=30/1"
        },
        "tee": {
            "linkable": "queue"
        },
        "convert_filter": {
            "caps": "video/x-raw,format=NV12,width=640,height=480,framerate=30/1"
        },
        "encoder_filter": {
            "caps": "video/x-h264, profile=main"
        },
        "mux": {
            "faststart": True
        },
        "sink": {
            "location": "output.mp4",
            "sync": False,
            "linkable": None
        },
        "queue": {
            "leaky": 2,
            "max-size-buffers": 1
        },
        "scale_filter": {
            "caps": "video/x-raw,format=RGB,width=320,height=320,framerate=30/1"
        },
        "appsink": {
            "drop": True,
            "max-buffers": 1,
            "emit-signals": True,
            "signals": {
                "new-sample": [on_new_sample, pipeline.get("source")]
            }
        },
        "timeout": 10
    })

    # Run both pipelines
    client.run()

    print("All done.")
