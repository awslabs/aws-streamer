
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

'''
This example shows how to attach buffer probe to any plug-in and consume
image buffer returned by the probe.

Probe can be attached to any pad of any plugin. Syntax:

"<plugin_name>": {
    "probes": {
        "<pad_name>": <callback_function>
    }
}

'''

import gstaws

def my_callback(buffer):
    '''
    This function will be called on every frame.
    Buffer is a ndarray, do with it what you like!
    '''
    print("Buffer info: %s, %s, %s" % (str(type(buffer)), str(buffer.dtype), str(buffer.shape)))


if __name__ == '__main__':

    # Initialize gstaws client
    client = gstaws.client()

    # Start a new pipeline synchronously
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
        "sink": {
            "probes": {
                "sink": my_callback
            }
        },
        "debug": True
    })

    print("All done.")
