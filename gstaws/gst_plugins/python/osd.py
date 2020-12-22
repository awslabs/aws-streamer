
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
    Plugin draws bounding boxes and text on frame from metadata

    From build folder:

    GST_PLUGIN_PATH=$PWD/libs gst-launch-1.0 videotestsrc ! \
        video/x-raw,format=RGBA,width=1280,height=720 ! timeoverlay ! \
        neodlr ! osd ! videoconvert ! fpsdisplaysink sync=false
"""

import logging
import timeit
import traceback
from typing import Tuple
import time
import cv2
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

DEFAULT_BORDER= 3
FORMATS = "{RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR}"


class GstOnScreenDisplay(GstBase.BaseTransform):

    GST_PLUGIN_NAME = 'osd'

    __gstmetadata__ = ("OnScreenDisplay",  # Name
                       "Filter",   # Transform
                       "Draws bounding boxes and text on the image",  # Description
                       "Bartek Pawlik <pawlikb@amazon.com>")  # Author

    __gsttemplates__ = (Gst.PadTemplate.new("src",
                                            Gst.PadDirection.SRC,
                                            Gst.PadPresence.ALWAYS,
                                            Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")),
                        Gst.PadTemplate.new("sink",
                                            Gst.PadDirection.SINK,
                                            Gst.PadPresence.ALWAYS,
                                            Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")))

    __gproperties__ = {

        "border": (GObject.TYPE_INT64,  # type
                   "Border Size",  # nick
                   "Element border size",  # blurb
                   1,  # min
                   GLib.MAXINT,  # max
                   DEFAULT_BORDER,  # default
                   GObject.ParamFlags.READWRITE  # flags
                   ),
    }

    def __init__(self):
        super(GstOnScreenDisplay, self).__init__()

        # Initialize properties before Base Class initialization
        self.border = DEFAULT_BORDER

    def do_get_property(self, prop: GObject.GParamSpec):
        if prop.name == 'border':
            return self.border
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop: GObject.GParamSpec, value):
        if prop.name == 'border':
            self.border = value
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_transform_ip(self, buffer: Gst.Buffer) -> Gst.FlowReturn:
        try:
            # convert Gst.Buffer to np.ndarray
            image = gst_buffer_with_caps_to_ndarray(buffer, self.sinkpad.get_current_caps())

            d = gst_meta_get(buffer)
            print("OSD:")
            print(d)
            for r in d:
                bb = r['bounding_box']
                cv2.rectangle(image, (bb[0], bb[1]), (bb[2], bb[3]), (0,255,0), self.border)

        except Exception as e:
            logging.error(e)

        return Gst.FlowReturn.OK


# Register plugin dynamically
GObject.type_register(GstOnScreenDisplay)
__gstelementfactory__ = (GstOnScreenDisplay.GST_PLUGIN_NAME,
                         Gst.Rank.NONE, GstOnScreenDisplay)
