
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
    Plugin performs ML inference with SageMaker NEO optimized model

    From build folder:

    GST_PLUGIN_PATH=$PWD/libs gst-launch-1.0 videotestsrc ! \
        video/x-raw,format=RGBA,width=1280,height=720 ! timeoverlay ! \
        neodlr ! osd ! videoconvert ! fpsdisplaysink sync=false
"""

from dlr.counter.phone_home import PhoneHome
PhoneHome.disable_feature()
from dlr import DLRModel

import logging
import timeit
import traceback
from typing import Tuple
import time
import cv2
import numpy as np
import os

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

class GstNeoDLR(GstBase.BaseTransform):

    GST_PLUGIN_NAME = 'neodlr'

    __gstmetadata__ = ("NeoDLR",  # Name
                       "Filter",   # Transform
                       "ML Inference with SageMaker Neo",  # Description
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

        "model-dir": (GObject.TYPE_STRING,  # type
                   "Model directory",  # nick
                   "SageMaker Neo model directory",  # blurb
                   DEFAULT_MODEL_DIR,  # default
                   GObject.ParamFlags.READWRITE  # flags
                   ),

        "device-type": (GObject.TYPE_STRING,  # type
                   "Device type",  # nick
                   "Device type: cpu or gpu",  # blurb
                   DEFAULT_DEVICE_TYPE,  # default
                   GObject.ParamFlags.READWRITE  # flags
                   ),

        "image-size": (GObject.TYPE_INT64,  # type
                   "Image Size",  # nick
                   "Image size for inference, width or height",  # blurb
                   1,  # min
                   GLib.MAXINT,  # max
                   DEFAULT_IMAGE_SIZE,  # default
                   GObject.ParamFlags.READWRITE  # flags
                   ),

        "threshold": (GObject.TYPE_FLOAT,
                   "Detection threshold",
                   "Detection threshold under which detection result will be ignored",
                   0.0,  # min
                   1.0,  # max
                   DEFAULT_THRESHOLD,  # default
                   GObject.ParamFlags.READWRITE
                   ),
    }

    def __init__(self):

        super(GstNeoDLR, self).__init__()

        # Initialize properties before Base Class initialization
        self.model_dir = DEFAULT_MODEL_DIR
        self.device_type = DEFAULT_DEVICE_TYPE
        self.image_size = DEFAULT_IMAGE_SIZE
        self.threshold = DEFAULT_THRESHOLD
        self.model = None

    def do_get_property(self, prop: GObject.GParamSpec):
        if prop.name == 'model-dir':
            return self.model_dir
        elif prop.name == 'device-type':
            return self.device_type
        elif prop.name == 'image-size':
            return self.image_size
        elif prop.name == 'threshold':
            return self.threshold
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def load_model(self):
        if self.model is not None:
            return
        if self.model_dir == "":
            return
        if os.path.exists(self.model_dir):
            # Load model
            print("Loading model from %s..." % self.model_dir)
            self.model = DLRModel(self.model_dir, self.device_type)
            print("Done.")

            print ("Warming up DLR engine...")
            start_time = time.time()
            x = np.random.rand(1, 3, self.image_size, self.image_size)
            result = self.model.run(x)
            print(len(result))
            print(result[0].shape)
            print('inference time is ' + str((time.time()-start_time)) + ' seconds')
            print ("Done.")

    def do_set_property(self, prop: GObject.GParamSpec, value):
        if prop.name == 'model-dir':
            self.model_dir = value
        elif prop.name == 'device-type':
            self.device_type = value
        elif prop.name == 'image-size':
            self.image_size = value
        elif prop.name == 'threshold':
            self.threshold = value
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_transform_ip(self, buffer: Gst.Buffer) -> Gst.FlowReturn:
        try:
            # Load the model
            if self.model is None:
                self.load_model()

            # Check if model has been loaded
            if self.model is None:
                return Gst.FlowReturn.OK

            # convert Gst.Buffer to np.ndarray
            image = gst_buffer_with_caps_to_ndarray(buffer, self.sinkpad.get_current_caps())

            print('Testing inference...')
            start_time = time.time()
            # img_rand = np.random.rand(1, 3, 320, 320)

            # Prepare input
            image_3 = image[:,:,:3]
            img_small = cv2.resize(image_3, (self.image_size, self.image_size))
            img_reshaped = np.reshape(img_small, (1, 3, self.image_size, self.image_size))

            # # Normalize & transpose
            # mean_vec = np.array([0.485, 0.456, 0.406])
            # stddev_vec = np.array([0.229, 0.224, 0.225])
            # img_reshaped = (img_reshaped/255 - mean_vec)/stddev_vec
            # img_reshaped = np.rollaxis(img_reshaped, axis=2, start=0)[np.newaxis, :]

            # Run inference
            result = self.model.run(img_reshaped)
            print('inference time is ' + str((time.time()-start_time)) + ' seconds')

            # Process inference output
            temp = []
            for r in result:
                r = np.squeeze(r)
                temp.append(r.tolist())
            idx, score, bbox = temp
            bbox = np.asarray(bbox)
            res = np.hstack((np.column_stack((idx, score)), bbox))
            l = list()
            for r in res:
                (class_id, score, x0, y0, x1, y1) = r
                if score < self.threshold:
                    continue
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
GObject.type_register(GstNeoDLR)
__gstelementfactory__ = (GstNeoDLR.GST_PLUGIN_NAME,
                         Gst.Rank.NONE, GstNeoDLR)
