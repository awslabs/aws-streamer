
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import glob
import logging
import subprocess
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GLib
from .stream_pipeline import StreamPipeline
from .stream_config import StreamConfig
from .stream_graph import StreamGraph

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CommandLinePipeline(StreamPipeline):
    def __init__(self, config):
        logger.info("Initializing %s..." % self.__class__.__name__)
        super().__init__(config)
        self.command = config["command"]

        # Add relative path if command is in gst_plugins
        if "path" in config and config["path"].startswith("gst_plugins"):
            plugin_path = "../"
            cwd_path = os.getcwd()
            file_path = os.path.abspath(os.path.dirname(__file__))
            if len(file_path) > len(cwd_path):
                diff_path = file_path.replace(cwd_path, '')
                diff_path = os.path.normpath(diff_path)
                plugin_path = os.path.join(diff_path, plugin_path)[1:]
            self.command[0] = os.path.join(plugin_path, config["path"], self.command[0])

    def build(self, config):
        logger.info("Building %s..." % self.__class__.__name__)
        pass

    def configure(self, config):
        logger.info("Configuring %s..." % self.__class__.__name__)
        pass

    def start(self):
        logger.info("Starting %s..." % self.__class__.__name__)
        logger.info(self.command)
        subprocess.check_call(self.command)
