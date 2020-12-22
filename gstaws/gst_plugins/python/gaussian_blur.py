#!/usr/bin/python

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
    Plugin blurs incoming buffer

    export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD

    gst-launch-1.0 videotestsrc ! gaussian_blur kernel=9 sigmaX = 5.0 sigmaY=5.0 ! videoconvert ! autovideosink
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

DEFAULT_KERNEL_SIZE = 3
DEFAULT_SIGMA_X = 1.0
DEFAULT_SIGMA_Y = 1.0

def gaussian_blur(img: np.ndarray, kernel_size: int = 3, sigma: Tuple[int, int] = (1, 1)) -> np.ndarray:
    """ Blurs image
    :param img: [height, width, channels >= 3]
    :param kernel_size:
    :param sigma: (int, int)
    """
    sigmaX, sigmaY = sigma
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), sigmaX=sigmaX, sigmaY=sigmaY)


FORMATS = "{RGBx,BGRx,xRGB,xBGR,RGBA,BGRA,ARGB,ABGR,RGB,BGR}"

class GstGaussianBlur(GstBase.BaseTransform):

    GST_PLUGIN_NAME = 'gaussian_blur'

    __gstmetadata__ = ("GaussianBlur",  # Name
                       "Filter",   # Transform
                       "Apply Gaussian Blur to Buffer",  # Description
                       "Bartek Pawlik <pawlikb@amazon.com>")  # Author

    __gsttemplates__ = (Gst.PadTemplate.new("src",
                                            Gst.PadDirection.SRC,
                                            Gst.PadPresence.ALWAYS,
                                            Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")),
                        Gst.PadTemplate.new("sink",
                                            Gst.PadDirection.SINK,
                                            Gst.PadPresence.ALWAYS,
                                            Gst.Caps.from_string(f"video/x-raw,format={FORMATS}")))

    # Explanation: https://python-gtk-3-tutorial.readthedocs.io/en/latest/objects.html#GObject.GObject.__gproperties__
    # Example: https://python-gtk-3-tutorial.readthedocs.io/en/latest/objects.html#properties
    __gproperties__ = {

        # Parameters from cv2.gaussian_blur
        # https://docs.opencv.org/3.0-beta/modules/imgproc/doc/filtering.html#gaussianblur
        "kernel": (GObject.TYPE_INT64,  # type
                   "Kernel Size",  # nick
                   "Gaussian Kernel Size",  # blurb
                   1,  # min
                   GLib.MAXINT,  # max
                   DEFAULT_KERNEL_SIZE,  # default
                   GObject.ParamFlags.READWRITE  # flags
                   ),

        # https://lazka.github.io/pgi-docs/GLib-2.0/constants.html#GLib.MAXFLOAT
        "sigmaX": (GObject.TYPE_FLOAT,
                   "Standart deviation in X",
                   "Gaussian kernel standard deviation in X direction",
                   1.0,  # min
                   GLib.MAXFLOAT,  # max
                   DEFAULT_SIGMA_X,  # default
                   GObject.ParamFlags.READWRITE
                   ),

        "sigmaY": (GObject.TYPE_FLOAT,
                   "Standart deviation in Y",
                   "Gaussian kernel standard deviation in Y direction",
                   1.0,  # min
                   GLib.MAXFLOAT,  # max
                   DEFAULT_SIGMA_Y,  # default
                   GObject.ParamFlags.READWRITE
                   ),
    }

    def __init__(self):
        super(GstGaussianBlur, self).__init__()

        # Initialize properties before Base Class initialization
        self.kernel_size = DEFAULT_KERNEL_SIZE
        self.sigma_x = DEFAULT_SIGMA_X
        self.sigma_y = DEFAULT_SIGMA_Y

    def do_set_caps(self, incaps, outcaps):
        struct = incaps.get_structure(0)
        self.width = struct.get_int("width").value
        self.height = struct.get_int("height").value
        return True

    def do_get_property(self, prop: GObject.GParamSpec):
        if prop.name == 'kernel':
            return self.kernel_size
        elif prop.name == 'sigmaX':
            return self.sigma_x
        elif prop.name == 'sigmaY':
            return self.sigma_y
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop: GObject.GParamSpec, value):
        if prop.name == 'kernel':
            self.kernel_size = value
        elif prop.name == 'sigmaX':
            self.sigma_x = value
        elif prop.name == 'sigmaY':
            self.sigma_y = value
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_transform_ip(self, buffer: Gst.Buffer) -> Gst.FlowReturn:
        try:
            # convert Gst.Buffer to np.ndarray
            image = gst_buffer_with_caps_to_ndarray(buffer, self.sinkpad.get_current_caps())

            # apply gaussian blur to image
            image[:] = gaussian_blur(image, self.kernel_size, sigma=(self.sigma_x, self.sigma_y))
        except Exception as e:
            logging.error(e)

        return Gst.FlowReturn.OK


# Required for registering plugin dynamically
# Explained:
# http://lifestyletransfer.com/how-to-write-gstreamer-plugin-with-python/
GObject.type_register(GstGaussianBlur)
__gstelementfactory__ = (GstGaussianBlur.GST_PLUGIN_NAME,
                         Gst.Rank.NONE, GstGaussianBlur)
