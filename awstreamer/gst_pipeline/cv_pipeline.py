
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import glob
import logging
import cv2
import numpy as np

try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import GObject, Gst, GLib
except:
    pass

import awstreamer
from awstreamer.gst_pipeline.stream_pipeline import StreamPipeline

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class OpenCvPipeline(StreamPipeline):
    def __init__(self, config):
        logger.info("Initializing %s..." % self.__class__.__name__)
        super().__init__(config)

        # OpenCV source element
        src = config["source"]
        self.source = cv2.VideoCapture(src["name"])
        self.min_idx = src["min_idx"] if "min_idx" in src else -1
        self.max_idx = src["max_idx"] if "max_idx" in src else -1
        self.step = src["step"] if "step" in src else 1
        self.restart = src["restart"] if "restart" in src else False
        self.rotate = src["rotate"] if "rotate" in src else False

        # OpenCV sink element
        self.sink_output = None
        if config.isSet("sink.output"):
            output = config.get("sink.output")
            width = int(config.get("sink.width"))
            height = int(config.get("sink.height"))
            fps = int(config.get("sink.fps"))
            if isinstance(output, str):
                outstr = output.strip()
                if ".mp4" in outstr:
                    fourcc = cv2.VideoWriter_fourcc('m','p','4','v')
                    self.sink_output = cv2.VideoWriter(outstr, fourcc, fps, (width, height))
            elif isinstance(output, dict):
                pipeline = config.get("sink.output.pipeline")
                outstr = "appsrc"
                for k,v in pipeline.items():
                    outstr += " ! " + v
                logger.info(outstr)
                self.sink_output = cv2.VideoWriter(outstr, cv2.CAP_GSTREAMER, 0, fps, (width, height))

            backened = self.sink_output.getBackendName()
            logger.info("Backend: %s" % backened)

            if self.sink_output.isOpened():
                logger.info("Successfully opened '%s' for writing" % outstr)
            else:
                logger.error("Couldn't open '%s' for writing" % outstr)
                self.sink_output = None

        # GStreamer sink pipeline
        self.sink_pipeline = None
        if config.isSet("sink.pipeline"):
            client = awstreamer.client()
            self.sink_pipeline, self.sink_thread = client.start(config.get("sink.pipeline"), wait_for_finish=False)
            self.sink_width = self.sink_pipeline.config.get("source.width")
            self.sink_height = self.sink_pipeline.config.get("source.height")
            self.sink_fps = self.sink_pipeline.config.get("source.fps")

        # OpenCV source display window
        self.source_window_name = None
        if config.get("source.display"):
            if isinstance(config.get("source.display"), str):
                self.source_window_name = config.get("source.display")
            else:
                self.source_window_name = "input"

        # OpenCV sink display window
        self.sink_window_name = None
        if config.get("sink.display"):
            if isinstance(config.get("sink.display"), str):
                self.sink_window_name = config.get("sink.display")
            else:
                self.sink_window_name = "output"

        # Overwrite process function
        if config.isSet("process"):
            self.process = config.get("process")

    def build(self, config):
        logger.info("Building %s..." % self.__class__.__name__)
        pass

    def configure(self, config):
        logger.info("Configuring %s..." % self.__class__.__name__)
        pass

    def process(self, img):
        return img

    def start(self):
        logger.info("Starting %s..." % self.__class__.__name__)

        index = self.min_idx

        while True:

            # Get desired frame from the video feed
            if index > -1:
                self.source.set(1, index)

            # Capture frame
            ret, img = self.source.read()

            if not ret or img is None:
                if self.restart:
                    if self.min_idx > -1:
                        index = self.min_idx
                    else:
                        self.source.set(1, 0)
                    logger.info("Probably end of video stream. Starting over...")
                    continue
                else:
                    logger.error("Can't receive frame (stream end?). Exiting ...")
                    break

            # Rotate 90 degrees clock-wise
            if self.rotate:
                img = cv2.transpose(img)
                img = cv2.flip(img, flipCode=1)

            # Display
            if self.source_window_name:
                cv2.imshow(self.source_window_name, img)

            # Process
            img = self.process(img)

            # Dump to sink output
            if self.sink_output is not None:
                self.sink_output.write(img)

            # Dump to sink pipeline
            if self.sink_pipeline is not None:
                img = cv2.resize(img, (self.sink_width, self.sink_height))
                self.sink_pipeline.push(img)

            # Display
            if self.sink_window_name:
                cv2.imshow(self.sink_window_name, img)

            if self.source_window_name or self.sink_window_name:
                cv2.waitKey(1)

            # Increment
            if index > -1:
                index += self.step
                if self.max_idx > -1 and index > self.max_idx:
                    if self.restart:
                        index = self.min_idx
                        logger.info("End of clip. Restarting...")
                    else:
                        break

    def stop(self):
        # Closing all open windows
        cv2.destroyAllWindows()

        # Stop sink pipeline
        if self.sink_pipeline:
            self.thread_pipeline.join()
