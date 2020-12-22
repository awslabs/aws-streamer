#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import pyds
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GLib

from .stream_pipeline import StreamPipeline
from .stream_config import StreamConfig
from .stream_graph import StreamGraph
from .video_pipeline import VideoPipeline

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DeepStreamPipeline(StreamPipeline):
    def __init__(self, config):
        logger.info("Initializing %s..." % self.__class__.__name__)
        super().__init__(config)

    def build(self, config):
        logger.info("Building %s..." % self.__class__.__name__)

        # Source
        VideoPipeline.add_source(self.graph, config)

        # DeepStream pipeline
        self.graph.add_pipeline({
            "decoder": "decodebin",
            "nvstreammux": "nvstreammux",
            "nvinfer": "nvinfer",
            "videoconvert": "nvvideoconvert",
            "overlay": "nvdsosd",
            "nvvideoconvert_2": "nvvideoconvert",
            "encoder": "x264enc",
            "encoder_filter": "capsfilter"
        })

        # Sink
        VideoPipeline.add_sink(self.graph, config)

    def configure(self, config):
        logger.info("Configuring %s..." % self.__class__.__name__)

        # Configure source pipeline
        VideoPipeline.configure_source(self.graph, config, link_filesrc=True)

        # Configure late decoder --> mux linking
        self.graph.get("decoder").linkable = False

        # Configure nvstreammux
        sinkpad = self.graph["nvstreammux"].get_request_pad("sink_0")
        if sinkpad is None:
            logger.error("Unable to get the sink pad of streammux \n")

        # Lets add probe to get informed of the meta data generated, we add probe to
        # the sink pad of the osd element, since by that time, the buffer would have
        # had got all the metadata.
        if config.isSet("callback"):
            pad = self.graph["overlay"].get_static_pad("sink")
            if not pad:
                logger.error(" Unable to get sink pad of nvosd \n")
            else:
                pad.add_probe(Gst.PadProbeType.BUFFER, self.pad_buffer_probe, config["callback"])

        # Configure sink pipeline
        VideoPipeline.configure_sink(self.graph, config)

    def pad_buffer_probe(self, pad, info, func):
        '''
        Parse DeepStream metadata and send it over to the callback function.
        Probe should be attached to either src or sink of plug-ins after nvinfer in the pipeline.
        '''
        # Get the gst buffer
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            logger.error("Unable to get GstBuffer ")
            return Gst.PadProbeReturn.OK

        # Retrieve batch metadata from the gst_buffer
        # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
        # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        frame_meta_list = batch_meta.frame_meta_list
        while frame_meta_list is not None:
            try:
                # Note that frame_meta_list.data needs a cast to pyds.NvDsFrameMeta
                # The casting is done by pyds.glist_get_nvds_frame_meta()
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave
                # it alone.
                frame_meta = pyds.NvDsFrameMeta.cast(frame_meta_list.data)
            except StopIteration:
                break

            frame_number = frame_meta.frame_num
            num_rects = frame_meta.num_obj_meta
            obj_meta_list = frame_meta.obj_meta_list
            object_list = []
            while obj_meta_list is not None:
                try:
                    obj_meta = pyds.NvDsObjectMeta.cast(obj_meta_list.data)
                except StopIteration:
                    break

                # Add object info to the list
                bbox = obj_meta.rect_params
                object_info = {
                    "class_id": obj_meta.class_id,
                    "confidence": obj_meta.confidence,
                    "bbox": [bbox.left, bbox.top, bbox.width, bbox.height]
                }
                object_list.append(object_info)

                # Move to the next object
                try:
                    obj_meta_list = obj_meta_list.next
                except StopIteration:
                    break

            # Collect metadata and call callback function
            if len(object_list) > 0:
                metadata = {
                    "frame_number": frame_number,
                    "num_rects": num_rects,
                    "objects": object_list
                }
                func(metadata)

            # Move to the next frame
            try:
                frame_meta_list = frame_meta_list.next
            except StopIteration:
                break

        return Gst.PadProbeReturn.OK
