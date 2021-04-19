#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import time
import argparse
import logging
from pprint import pformat
from pebble import ProcessPool
from threading import Thread

from .stream_config import StreamConfig
from .pipeline_factory import PipelineFactory
from ..utils.aws import is_greengrass_enabled, is_ecs_enabled

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GLib
Gst.init(None)

# Create a global logger
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


def stream_pipeline(id, params):
    '''
    Creates and starts a new GStreamer pipeline.
    This cannot be a member of a StreamClient to conform with Python3.6 limitations.
    '''
    try:
        # Update config
        params["id"] = id
        config = StreamConfig(params)
        logger.info(pformat(config))

        # Get pipeline
        pipeline = PipelineFactory.createPipeline(config)

        # Start pipeline
        pipeline.start()

    except Exception as e:
        logger.error("Failed to run StreamPipeline: " + repr(e))
        raise e

class StreamClient():
    '''
    Client managing all stream pipelines
    '''

    # Maximum number of cameras that can be configured
    MAX_PIPELINE_COUNT = 20

    def __init__(self):
        # Initialize concurrent engine
        self.pool = ProcessPool(max_workers=StreamClient.MAX_PIPELINE_COUNT+1, max_tasks=StreamClient.MAX_PIPELINE_COUNT)
        self.futures = dict()
        self.set_env_variables()
        self.config = dict()
        self.pipelines = dict()

    def set_env_variables(self):
        '''
        Sets GStreamer environmental variables
        '''
        # Logging level
        if 'GST_DEBUG' not in os.environ:
            os.environ['GST_DEBUG'] = '2,splitmuxsink:4'

        # Plugin path
        plugin_path = "../gst_plugins"
        cwd_path = os.getcwd()
        file_path = os.path.abspath(os.path.dirname(__file__))
        if len(file_path) > len(cwd_path):
            diff_path = file_path.replace(cwd_path, '')
            diff_path = os.path.normpath(diff_path)
            plugin_path = os.path.join(diff_path, plugin_path)[1:]

        # Python bindings path
        plugin_path += ":/usr/lib/gstreamer-1.0/"

        logger.info("GST_PLUGIN_PATH: %s" % plugin_path)
        os.environ["GST_PLUGIN_PATH"] = plugin_path

        # Set LIB_GSTREAMER_PATH
        if 'LIB_GSTREAMER_PATH' not in os.environ:
            logger.info("Gstreamer version: {}.{}.{}.{}".format(*Gst.version()))
            lib_gst_path = None
            if sys.platform == "darwin":
                lib_gst_path = "/usr/local/Cellar/gstreamer/{}.{}.{}/lib/libgstreamer-1.0.dylib".format(*Gst.version())
            elif sys.platform == "win32":
                lib_gst_path = "C:\\msys64\\mingw64\\bin\\libgstreamer-1.0-0.dll"
            else:
                lib_gst_paths = [
                    "/usr/lib/aarch64-linux-gnu/libgstreamer-1.0.so.0",
                    "/usr/lib/x86_64-linux-gnu/libgstreamer-1.0.so.0"
                ]
                for path in lib_gst_paths:
                    if os.path.exists(path):
                        lib_gst_path = path
                        break

            if lib_gst_path is None:
                logger.warning("libgstreamer-1.0 not found! Please export LIB_GSTREAMER_PATH env var manually.")
            else:
                logger.info("LIB_GSTREAMER_PATH: %s" % lib_gst_path)
                os.environ['LIB_GSTREAMER_PATH'] = lib_gst_path

    def update(self, config):
        '''
        Merge new config with existing one
        '''
        self.config.update(config)

    def get_config(self, config_or_filename):
        '''
        Load config from file and return it in dictionary format
        '''
        if config_or_filename is None or isinstance(config_or_filename, str):
            return StreamConfig.LoadConfigFromFile(config_or_filename)
        else:
            return config_or_filename

    def get_pipeline(self, name):
        '''
        Returns pipeline with a given name
        '''
        if name in self.pipelines:
            return self.pipelines[name]
        return None

    def add(self, config_or_filename=None):
        '''
        Build pipeline and add to the registry
        '''
        # Get config in the proper format
        config = self.get_config(config_or_filename)

        # Add default id if config is flat
        if config is not None and "pipeline" in config:
            key = "default_%d" % len(self.pipelines.keys())
            config = { key: config }

        for key in config:
            # Skip those sources that are disabled in configuration
            if "enabled" in config[key] and not config[key]["enabled"]:
                logger.info("Skipping %s (disabled)" % key)
                continue

            # Parse config
            config[key]["id"] = key
            pipeline_config = StreamConfig(config[key])
            logger.info(pformat(pipeline_config))

            # Create pipeline
            pipeline = PipelineFactory.createPipeline(pipeline_config)
            self.pipelines[key] = pipeline

        if len(self.pipelines.keys()) == 1:
            return tuple(self.pipelines.values())[0]

        return tuple(self.pipelines.values())

    def run(self, loop=None):
        '''
        Run pipelines that have been added with add()
        '''
        if len(self.pipelines.keys()) == 0:
            logger.error("No pipelines added")
            return

        # Main application loop
        if loop is None:
            loop = GLib.MainLoop()

        # Start each pipeline
        for k,v in self.pipelines.items():
            v.start(loop)

        # Run the main loop
        loop.run()

        # Cleanup when main loop has ended
        for k,v in self.pipelines.items():
            v.stop()

    def start(self, config_or_filename=None, wait_for_finish=True):
        '''
        Start single pipeline
        '''
        pipeline = self.add(config_or_filename)
        if wait_for_finish:
            self.run()
        else:
            thread = Thread(target=self.run)
            thread.start()
            return pipeline, thread

    def stop(self):
        self.pool.stop()

    def schedule(self, config_or_filename=None, wait_for_finish=False, restart_on_exception=False):
        '''
        Start one or more pipelines asynchronously, in parallel
        '''
        try:
            # Get config in the proper format
            config = self.get_config(config_or_filename)

            # Update cached config
            self.update(config)

            # Check for misuse of schedule()
            for i in ['debug', 'enabled']:
                if i in config and isinstance(config[i], bool):
                    logger.error("Either use start() instead of schedule() or nest the configuration into a pipeline.")
                    return config

            # Stop pipelines that are going to be reconfigured
            for key in self.futures:
                if key in config:
                    logger.info("Cancelling the following pipeline: %s" % key)
                    if self.futures[key].cancel() == False:
                        logger.error("Failed to cancel the following pipeline: %s" % key)
                        continue

            # Spin off each camera pipeline in a separate thread/process
            for key in config:
                # Cap at MAX_PIPELINE_COUNT
                if len(self.futures.keys()) >= StreamClient.MAX_PIPELINE_COUNT:
                    logger.error("Maximum number of pipelines reached. Not configuring %s" % key)
                    continue

                # Skip those sources that are disabled in configuration
                if "enabled" in config[key] and not config[key]["enabled"]:
                    logger.info("Skipping %s (disabled)" % key)
                    del self.config[key]
                    continue

                # Start new process/thread
                future = self.pool.schedule(stream_pipeline, args=[key, config[key]])
                if restart_on_exception:
                    future.add_done_callback(self.catch_and_restart)
                self.futures[key] = future

            # This is a blocking call, therefore use with caution (it will prevent parallel execution!)
            if wait_for_finish:
                for key in self.futures:
                    logger.info(self.futures[key].result())

        except Exception as e:
            logger.error("Failed to start pipeline(s): " + repr(e))
            self.config["error"] = repr(e)

        return self.config

    def catch_and_restart(self, future):
        '''
        Catches any exception from the future and restarts the process/thread
        '''
        try:
            result = future.result()
            logger.info(result)
        except TimeoutError as error:
            logger.error("Function took longer than %d seconds" % error.args[1])
        except Exception as error:
            logger.error("Function raised %s" % error)

            if "CancelledError" in error.__class__.__name__:
                logger.error("Function has been already cancelled. Doing nothing...")
                return

            if hasattr(error, 'traceback'):
                logger.error(error.traceback)

            logger.info("Restarting all pipelines after 5 sec...")
            time.sleep(5)
            self.schedule(self.config, wait_for_finish=False, restart_on_exception=True)

if __name__ == "__main__":
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=str, nargs='?', default="config.json", help="Configuration file")
    args = parser.parse_args()
    logger.info(args)

    # Start an app
    client = StreamClient()
    client.schedule(args.config)
