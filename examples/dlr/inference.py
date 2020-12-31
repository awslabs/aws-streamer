'''
1. Grab frame, report inference results numerically
2. Grab frame, report inference results numerically, record original stream
3. Grab frame, report inference results numerically, overlay inference results
4. Grab frame, report inference results numerically, record original stream + overlay inference results

1. appsink drop=True max-buffers=1 emit-signals=True max-lateness=8000000000
2. tee + appsink, tee + filesink
3. appsink + appsrc
4. tee + appsink + appsrc, tee + filesink

'''

import os
import awstreamer
from dlr import DLRModel
from pprint import pformat
from time import sleep
import datetime

dir_path = os.path.abspath(os.path.dirname(__file__))

# Initialize awstreamer client
client = awstreamer.client()

counter = 0
def my_callback(buffer):
    '''
    This function will be called on every frame.
    Buffer is a ndarray, do with it what you like!
    '''
    global counter
    global client

    # print("Buffer info: %s, %s, %s" % (str(type(buffer)), str(buffer.dtype), str(buffer.shape)))
    print(counter)
    counter += 1
    sleep(1)

    print(datetime.datetime.now())

    # p = client.get_pipeline("display")
    # appsource = p["source"]
    # appsource.emit("push-buffer", Gst.Buffer.new_wrapped(img.tobytes()))

    return Gst.FlowReturn.OK


if __name__ == '__main__':

    client.start({
        "main": {
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
                "linkable": None
            },
            "queue": {
                "leaky": 2
            },
            "appsink": {
                "drop": True,
                "max-buffers": 1,
                "emit-signals": True,
                "signals": {
                    "new-sample": [my_callback]
                }
            },
            "timeout": 5
        },
        "display": {
            "pipeline": {
                "source": "appsrc",
                "sink": "autovideosink"
            },
            "source": {
                "is-live": True,
                "block": True
            }
        }
    })

    print("All done.")
