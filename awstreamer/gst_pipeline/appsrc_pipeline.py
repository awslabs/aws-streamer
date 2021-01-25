
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import glob
import logging

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GLib

from .stream_pipeline import StreamPipeline
from .stream_config import StreamConfig
from .stream_graph import StreamGraph
from .video_pipeline import VideoPipeline

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AppSrcPipeline(StreamPipeline):
    def __init__(self, config):
        logger.info("Initializing %s..." % self.__class__.__name__)
        super().__init__(config)

    def build(self, config):
        logger.info("Building %s..." % self.__class__.__name__)

        # Source
        self.graph.add_pipeline({
            "source": "appsrc",
            "source_filter": "capsfilter",
            "convert": "videoconvert"
        })

        # Encoder
        if config.get("sink.name") == "hlssink":
            self.graph.add("x264enc", "encoder")
            self.graph.add("capsfilter", "encoder_filter")

        # Sink
        VideoPipeline.add_sink(self.graph, config)

    def configure(self, config):
        logger.info("Configuring %s..." % self.__class__.__name__)

        # Configure source
        self.graph["source"].set_property("name", "source")
        self.graph["source"].set_property("emit-signals", True)
        self.graph["source"].set_property("do-timestamp", True)
        self.graph["source"].set_property("is-live", True)
        self.graph["source"].set_property("block", True)
        self.graph["source"].set_property("format", 3)

        # Configure source filter
        caps_str = 'video/x-raw,format=BGR,width=%d,height=%d,framerate=%d/1,interlace-mode=(string)progressive' \
            % (config.get("source.width"), config.get("source.height"), config.get("source.fps"))
        config["source_filter"] = { "caps": caps_str }
        source_caps = Gst.caps_from_string(caps_str)
        self.graph["source_filter"].set_property("caps", source_caps)

        # Configure encoder_filter
        if self.graph.contains("encoder_filter"):
            caps_str = 'video/x-h264, profile=main'
            config["encoder_filter"] = { "caps": caps_str }
            encoder_caps = Gst.caps_from_string(caps_str)
            self.graph["encoder_filter"].set_property("caps", encoder_caps)

        # Configure sink pipeline
        VideoPipeline.configure_sink(self.graph, config)

    def push(self, img):
        self.get("source").emit("push-buffer", Gst.Buffer.new_wrapped(img.tobytes()))
