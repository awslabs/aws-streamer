#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

set -xeo pipefail

X_SERVER_NUM=1

echo ${QUEUE_NAME}

python3 /aws-stream-sdk/examples/serverless/run.py ${QUEUE_NAME}
