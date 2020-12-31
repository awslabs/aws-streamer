
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
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

class VideoRecorderPipeline(StreamPipeline):
    def __init__(self, config):
        logger.info("Initializing %s..." % self.__class__.__name__)
        super().__init__(config)

    def build(self, config):
        logger.info("Building %s..." % self.__class__.__name__)

        # Source
        VideoPipeline.add_source(self.graph, config)

        # Sink
        self.graph.add("splitmuxsink", "sink")

    def configure(self, config):
        logger.info("Configuring %s..." % self.__class__.__name__)

        # Configure source pipeline
        VideoPipeline.configure_source(self.graph, config)

        # Configure video segment size
        if config.isSet("sink.segment_duration"):
            segment_duration = config.get("sink.segment_duration")
            segment_duration = segment_duration.split(':')
            segment_duration_hour = int(segment_duration[0])
            segment_duration_min = int(segment_duration[1])
            segment_duration_sec = int(segment_duration[2])
            segment_duration_total_sec = segment_duration_sec + 60 * (segment_duration_min + 60 * segment_duration_hour)
            logger.info("segment_duration_total_sec: %d" % segment_duration_total_sec)
            segment_duration_total_ns = 1000000000 * segment_duration_total_sec
            self.graph["sink"].set_property("max-size-time", segment_duration_total_ns)

        # Configure time-to-live for a video segment
        if config.isSet("sink.time_to_keep_days"):
            time_to_keep_days = config.get("sink.time_to_keep_days")
            time_to_keep_sec = time_to_keep_days * 24 * 60 * 60
            max_files = int(float(time_to_keep_sec) / float(segment_duration_total_sec))
            logger.info("time_to_keep_sec: %d" % time_to_keep_sec)
            logger.info("max_files: %d" % max_files)
            self.graph["sink"].set_property("max-files", max_files)

        # Configure muxer
        if not config.isSet("sink.muxer-factory"):
            mux = Gst.ElementFactory.make("qtmux", "mux")
            mux.set_property("faststart", True)
            self.graph["sink"].set_property("muxer", mux)

        # Create desitnation folder
        dest_dir = os.path.dirname(config.get("sink.location"))
        if dest_dir.strip() != "":
            logger.info("Destination directory: %s" % dest_dir)
            os.makedirs(dest_dir, mode=0o777, exist_ok=True)
