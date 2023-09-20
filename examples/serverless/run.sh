#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


export GST_PLUGIN_PATH=/aws-streamer/amazon-kinesis-video-streams-producer-sdk-cpp/build
export LD_LIBRARY_PATH=/aws-streamer/amazon-kinesis-video-streams-producer-sdk-cp/open-source/local/lib

X_SERVER_NUM=1

echo ${QUEUE_NAME}

python3 /aws-streamer/examples/serverless/run.py ${QUEUE_NAME}
