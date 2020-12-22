
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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class VideoPipeline(StreamPipeline):
    def __init__(self, config):
        logger.info("Initializing %s..." % self.__class__.__name__)
        super().__init__(config)

    @staticmethod
    def add_source(graph, config):
        graph.add(config.get("source.name"), "source")
        if config.get("source.name") == "rtspsrc":
            graph.add("rtph264depay", "depay")
            graph.add("h264parse", "parse")
        elif "filesrc" in config.get("source.name"):
            pass
        else:
            graph.add("capsfilter", "source_filter")
            graph.add("timeoverlay", "timeoverlay")
            graph.add("x264enc", "encoder")

    @staticmethod
    def add_sink(graph, config):
        if config.get("sink.name") == "hlssink":
            graph.add_pipeline({
                "mux": "mpegtsmux",
                "sink": "hlssink"
            })
        else:
            graph.add(config.get("sink.name") if config.isSet("sink.name") else "fakesink", "sink")

    @staticmethod
    def configure_source(graph, config, link_filesrc=False):
        # Configure late source linking
        if config.get("source.name") in ["rtspsrc"] or ("filesrc" in config.get("source.name") and not link_filesrc):
            graph.get("source").linkable = False

        # Configure source filter
        if graph.contains("source_filter"):
            caps_str = 'video/x-raw,width=%d,height=%d,framerate=%d/1' \
                % (config.get("source.width"), config.get("source.height"), config.get("source.fps"))
            logger.info(caps_str)
            source_caps = Gst.caps_from_string(caps_str)
            graph["source_filter"].set_property("caps", source_caps)

    @staticmethod
    def configure_sink(graph, config):
        if config.get("sink.name") == "hlssink":
            # Remove segments
            location = config.get("sink.location")
            if location:
                filename = location.split('%')[0]
                file_list = glob.glob(filename + '*')
                for f in file_list:
                    try:
                        os.remove(f)
                    except:
                        logger.warning("Error while deleting file: %s" % f)

    def build(self, config):
        logger.info("Building %s..." % self.__class__.__name__)

        # Add source pipeline to the graph
        VideoPipeline.add_source(self.graph, config)

        # Add sink pipeline to the graph
        VideoPipeline.add_sink(self.graph, config)

    def configure(self, config):
        logger.info("Configuring %s..." % self.__class__.__name__)

        # Configure source pipeline
        VideoPipeline.configure_source(self.graph, config)

        # Configure sink pipeline
        VideoPipeline.configure_sink(self.graph, config)
