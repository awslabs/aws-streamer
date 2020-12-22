#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import json
import logging
from pprint import pformat
import awstreamer
import greengrasssdk

# Create a global logger
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize AWS clients
gst_client = awstreamer.client()
gg_client = greengrasssdk.client("iot-data")

def lambda_handler(event, context):
    '''
    Event should be in the following format:
    {
        "camera_id_1": {
            "key", "value",
            ...
        },
        "camera_id_2": {
            ...
        },
        ...
    }
    '''
    global gst_client
    global gg_client
    global logger

    logger.info("Received message in lambda_handler:")
    logger.info(pformat(event))

    # Schedule new event
    result = gst_client.schedule(event)

    # Publish response
    try:
        topic = None
        if event is not None and "topic" in event:
            topic = event["topic"]
        elif "THING_NAME" in os.environ:
            topic = os.environ['THING_NAME'] + '/camera/feed'
        if topic is not None:
            logger.info("Publishing to topic: %s" % topic)
            gg_client.publish(
                topic=topic,
                queueFullPolicy="AllOrException",
                payload=json.dumps(result).encode("utf-8")
            )
    except Exception as e:
        logger.error("Failed to publish message: " + repr(e))


# Default configuration goes here. This will kick off after the deployment.
lambda_handler(None, None)
