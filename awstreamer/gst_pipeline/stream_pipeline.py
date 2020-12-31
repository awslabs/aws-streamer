#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging
from threading import Timer
import datetime
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GLib

from .stream_config import StreamConfig
from .stream_graph import StreamGraph
from ..utils.aws import get_aws_plugins_list, set_aws_env_variables
from ..utils.plugin import get_python_plugins_list
from ..utils.gst import gst_buffer_with_pad_to_ndarray

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

Gst.init(None)

class StreamPipeline(object):
    '''
    Class for orchestrating camera inference pipeline
    '''
    def __init__(self, config=None):
        logger.info("Initializing %s for %s.." % (self.__class__.__name__, config["id"]))

        if config is None:
            config = StreamConfig()

        self.debug = config["debug"]
        self.config = config
        self.name = "%s_%s" % (self.__class__.__name__, config["id"])

        self.loop = GLib.MainLoop()
        self.pipeline = None
        self.graph = StreamGraph()

        # Register callback functions
        self.graph.register_callback("on_pad_added", self.on_pad_added)
        self.graph.register_callback("buffer_probe_callback", self.buffer_probe_callback)

        # Build and configure pipeline
        self.build(self.config)
        self.configure(self.config)
        self.auto_configure(self.config)
        self.compile(self.config)

    def build(self, config):
        '''
        Virtual method, it can be overriden by a child
        '''
        # If python plugins are in pipeline, do parse_launch instead
        python_plugins = get_python_plugins_list()
        for k,v in config["pipeline"].items():
            if v in python_plugins:
                self.graph.parse_launch = True
                break

        # Build pipeline from dict
        if isinstance(config["pipeline"], dict):
            for k,v in config["pipeline"].items():
                logger.info("%s: %s" % (k,v))
                self.graph.add(v, k)
        elif isinstance(config["pipeline"], list):
            for i in range(len(config["pipeline"])):
                d = config["pipeline"][i]
                for k,v in d.items():
                    logger.info("%s: %s" % (k,v))
                    self.graphs[i].add(v, k)
        else:
            logger.error("Pipeline should be a dictionary or list of dictionaries!")

    def configure(self, config):
        '''
        Virtual method, it can be overriden by a child
        '''
        pass

    def auto_configure(self, config):
        '''
        Auto-configure plug-ins from the input configuration
        '''
        logger.info("Auto-configuring %s..." % self.__class__.__name__)

        # Configure plug-ins' parameters from the config
        for k,v in config.items():
            self.graph.configure(k, v)

        # Set AWS env variables if graph contains AWS plug-ins
        if self.graph.contains_plugin(get_aws_plugins_list()) or config["env"] == "aws":
            set_aws_env_variables()

    def compile(self, config):
        '''
        Compiles the pipeline: adds elements from the graph and links them
        '''
        logger.info("Compiling %s..." % self.__class__.__name__)

        if self.graph.parse_launch:
            gst_launch_str = self.graph.get_gst_launch_str(config, parse_launch=True)
            self.pipeline = Gst.parse_launch(gst_launch_str)
        else:
            self.pipeline = Gst.Pipeline()
            self.graph.compile(self.pipeline)

        # Log gst-launch-1.0 line for debugging
        gst_launch_str = self.graph.get_gst_launch_str(config, parse_launch=False)
        logger.info("gst-launch-1.0 " + gst_launch_str)

    def on_message(self, bus, message, udata):
        '''
        Callback function called on pipeline message
        '''
        pipeline, loop = udata

        if message.type == Gst.MessageType.EOS:
            loop.quit()
        elif message.type == Gst.MessageType.WARNING:
            logger.warning(message.parse_warning())
        elif message.type == Gst.MessageType.ERROR:
            logger.error(message.parse_error())
            loop.quit()

        return True

    def on_pad_added(self, src, new_pad, target):
        '''
        Callback function called on new pad added
        '''
        # Get new pad info
        new_pad_name = new_pad.get_name()
        new_pad_caps = new_pad.get_current_caps()
        new_pad_struct = new_pad_caps.get_structure(0)
        new_pad_type = new_pad_struct.get_name()

        logger.info("Received new pad '{0:s}' from '{1:s}'".format(
                new_pad_name,
                src.get_name()))
        logger.info(new_pad_caps.to_string())

        # Check payload type and set the blocking probe on audio
        add_block_probe = False
        if new_pad_type == "application/x-rtp" and new_pad_struct.has_field("media"):
            media_type = new_pad_struct.get_string("media")
            logger.info("Media type: %s" % media_type)
            if media_type != "video":
                add_block_probe = True
        elif new_pad_type.startswith("audio"):
            add_block_probe = True

        # Add blocking probe
        if add_block_probe:
            logger.info("Adding blocking probe to the pad: %s" % new_pad_name)
            new_pad.add_probe(Gst.PadProbeType.BLOCK, lambda x,y : Gst.PadProbeReturn.OK)
            return

        # Find target sink pad
        sink_pad = target.get_static_pad("sink")
        if not sink_pad:
            logger.info("Static sink pad not found for element '%s'. Searching by indices..." % target.name)
            for i in range(10):
                sink_pad = target.get_static_pad("sink_" + str(i))
                if sink_pad:
                    logger.info("Found static sink pad for element '%s': sink_%d" % (target.name, i))
                    break
        if not sink_pad:
            logger.error("Failed to find sink pad for element: %s" % target.name)

        if sink_pad.is_linked():
            logger.info("We are already linked. Ignoring.")
            return

        # Attempt the link
        ret = new_pad.link(sink_pad)
        if not ret == Gst.PadLinkReturn.OK:
            logger.info("Type is '{0:s}}' but link failed".format(new_pad_type))
        else:
            logger.info("Link succeeded (type '{0:s}')".format(new_pad_type))

    def buffer_probe_callback(self, pad, info, callback):
        '''
        Callback function called on buffer probe
        '''
        # Get the gst buffer
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            logger.error("Unable to get GstBuffer ")
            return Gst.PadProbeReturn.OK

        # Convert gst buffer to ndarray
        data = gst_buffer_with_pad_to_ndarray(gst_buffer, pad, do_copy=True)

        # User's callback function
        callback(data)

        return Gst.PadProbeReturn.OK

    def send_eos(self, pipeline):
        '''
        Callback function called on End-Of-Stream
        '''
        logger.info("Lights out!")
        pipeline.send_event(Gst.Event.new_eos())

    def start(self, loop=None):
        '''
        Sets pipeline to the playing state
        '''
        logger.info("Starting %s..." % self.__class__.__name__)
        bus = self.pipeline.get_bus()
        bus.add_watch(0, self.on_message, (self.pipeline, self.loop if loop is None else loop))

        # Set pipeline state to playing and check
        self.pipeline.set_state(Gst.State.PLAYING)
        logger.info(self.pipeline.get_state(Gst.CLOCK_TIME_NONE))
        if self.pipeline.get_state(Gst.CLOCK_TIME_NONE)[0] != Gst.StateChangeReturn.SUCCESS:
            logger.error("Failed to set the pipeline to the playing state")
            return

        # Create timer for end of stream
        if self.config.isSet("timeout"):
            delay = datetime.timedelta(seconds=self.config.get("timeout")).total_seconds()
            Timer(delay, self.send_eos, args=(self.pipeline,)).start()

        if loop is None:
            # Start the main loop, blocking call
            self.loop.run()

            # This will be called after main loop has ended
            self.pipeline.set_state(Gst.State.NULL)

    def stop(self):
        '''
        Stops pipeline and cleans up the resources
        '''
        self.pipeline.send_event(Gst.Event.new_eos())
        self.pipeline.set_state(Gst.State.NULL)
