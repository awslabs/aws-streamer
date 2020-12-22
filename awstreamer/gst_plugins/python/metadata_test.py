
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
    Plugin performs ML inference with SageMaker NEO optimized model

    From build folder:

    GST_PLUGIN_PATH=$PWD/libs gst-launch-1.0 videotestsrc ! \
        video/x-raw,format=RGBA,width=1280,height=720 ! timeoverlay ! \
        neodlr ! osd ! videoconvert ! fpsdisplaysink sync=false
"""

import random
import logging
import timeit
import traceback
from typing import Tuple
import time
import numpy as np

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GLib, GObject, GstBase, GstVideo

import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '../..'))
from utils.gst_hacks import map_gst_buffer
from utils.gst import gst_buffer_with_caps_to_ndarray
from gst_metadata.gst_objects_info_meta import gst_meta_get, gst_meta_write

DEFAULT_MODEL_DIR = ""
DEFAULT_DEVICE_TYPE = "cpu"
DEFAULT_IMAGE_SIZE = 320
DEFAULT_THRESHOLD = 0.0
FORMATS = "{RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR}"

class GstMetadataTest(GstBase.BaseTransform):

    GST_PLUGIN_NAME = 'metadata_test'

    __gstmetadata__ = ("MetadataTest",  # Name
                       "Filter",   # Transform
                       "Adds random metadata to the buffer",  # Description
                       "Bartek Pawlik <pawlikb@amazon.com>")  # Author

    __gsttemplates__ = (Gst.PadTemplate.new("src",
                                            Gst.PadDirection.SRC,
                                            Gst.PadPresence.ALWAYS,
                                            Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")),
                        Gst.PadTemplate.new("sink",
                                            Gst.PadDirection.SINK,
                                            Gst.PadPresence.ALWAYS,
                                            Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")))

    def __init__(self):
        super(GstMetadataTest, self).__init__()

    def do_transform_ip(self, buffer: Gst.Buffer) -> Gst.FlowReturn:
        try:
            # convert Gst.Buffer to np.ndarray
            image = gst_buffer_with_caps_to_ndarray(buffer, self.sinkpad.get_current_caps())
            h,w = image.shape[0:2]

            # Generate random ML inference results
            N = int(5 * random.random()) # [0-5)
            res = []
            for i in range(N):
                class_id = int((10 * random.random()) - 1) # [-1,9)
                score = random.random() # [0,1)
                x0 = random.random() * w # [0,w)
                y0 = random.random() * h # [0,h)
                width = 0.5 * random.random() * w
                height = 0.5 * random.random() * h
                x1 = min(x0 + width, w-1)
                y1 = min(y0 + height, h-1)
                res.append((class_id, score, x0, y0, x1, y1))

            l = []
            for r in res:
                (class_id, score, x0, y0, x1, y1) = r
                d = {
                    "bounding_box": (int(x0), int(y0), int(x1), int(y1)),
                    "confidence": score,
                    "class_name": "class_name",
                    "track_id": int(class_id)
                }
                l.append(d)
            print(l)
            gst_meta_write(buffer, l)

        except Exception as e:
            logging.error(e)

        return Gst.FlowReturn.OK


# Required for registering plugin dynamically
GObject.type_register(GstMetadataTest)
__gstelementfactory__ = (GstMetadataTest.GST_PLUGIN_NAME,
                         Gst.Rank.NONE, GstMetadataTest)
