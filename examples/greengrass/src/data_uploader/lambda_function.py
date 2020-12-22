
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
import json
from pprint import pformat
from data_handler import DataHandler

# Setup logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize data handler
handler = DataHandler()

def lambda_handler(event, context):
    '''
    Request file event should be in the following format:
    {
        "request": {
            ... # See request.json for request message fields
        }
    }

    To (re)configure Data Handler, use the the "config" keyword:
    {
        "config": {
            ... # See config.json for configuration options
        }
    }

    '''
    global logger
    global handler

    logger.info("Received message in lambda_handler:")
    logger.info(pformat(event))

    try:
        # Configure handler
        if "config" in event:
            handler.configure(event["config"])

        # Send files to S3
        if "request" in event:
            handler.uploadFilesToS3(event["request"])

    except Exception as e:
        logger.error("Failed to upload files to S3: " + repr(e))


# Load settings from the local JSON file
with open('config.json') as json_file:
    config = json.load(json_file)

# Default configuration goes here. This will kick off after the deployment.
lambda_handler(config, None)
