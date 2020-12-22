
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import importlib
import logging
from pydoc import locate

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PipelineFactory():
    @staticmethod
    def createPipeline(config):
        '''
        Return a class instance from a pipeline string
        '''
        # Get path to the pipeline class
        pipeline_path = PipelineFactory.getPipelinePath(config["pipeline"])
        logger.info("PipelineFactory: creating a pipeline from path: %s" % pipeline_path)

        # Get python version
        python_version = sys.version.split(' ')[0]
        logger.info("python_version: %s" % python_version)

        # If pipeline starts with dot (.), add relative path to it:
        if pipeline_path.startswith("."):
            # Root dir of the gstaws python package is assumed to be: ../../
            file_path = os.path.abspath(os.path.dirname(__file__))
            root_dir = os.path.abspath(os.path.dirname(os.path.dirname(file_path)))

            # Add subdir path
            if len(file_path) > len(root_dir):
                diff_path = file_path.replace(root_dir, '')
                diff_path = os.path.normpath(diff_path)
                arr = diff_path.split(os.sep)
                diff_path = '.'.join(arr[1:])
                pipeline_path = diff_path + pipeline_path

        try:
            class_ = locate(pipeline_path)
        except ImportError:
            logging.error('Module does not exist')

        return class_(config) or None

    @staticmethod
    def getPipelinePath(pipeline):
        '''
        Mapping from keywords to the pipeline module/class
        '''
        d = {
            "default": ".stream_pipeline.StreamPipeline",
            "dvr": ".dvr_pipeline.VideoRecorderPipeline",
            "video": ".video_pipeline.VideoPipeline",
            "deepstream": ".ds_pipeline.DeepStreamPipeline",
            "cmd": ".cmd_pipeline.CommandLinePipeline"
        }

        if isinstance(pipeline, dict):
            return d["default"]

        return d[pipeline.lower()] if pipeline.lower() in d else pipeline
