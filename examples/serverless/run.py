
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import argparse
import awstreamer
import boto3
import time
import json
import logging

for name in logging.Logger.manager.loggerDict.keys():
    if ('boto' in name) or ('urllib3' in name) or ('s3transfer' in name) or ('boto3' in name) or ('botocore' in name) or ('nose' in name):
        logging.getLogger(name).setLevel(logging.CRITICAL)

dir_path = os.path.abspath(os.path.dirname(__file__))
cwd = os.getcwd()

if __name__ == "__main__":
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('queue_name', type=str, nargs='?', default="test", help="SQS Queue Name")
    args = parser.parse_args()
    print(args)

    # Streaming client
    client = awstreamer.client()

    # Get the SQS client
    sqs = boto3.resource('sqs')

    # Get the queue(s)
    pull_queue = sqs.create_queue(QueueName=args.queue_name)
    push_queue = sqs.create_queue(QueueName=args.queue_name + "-res")

    # Main loop
    running = True
    print("Waiting for messages...")
    while running:
        try:
            # Process messages from SQS
            for message in pull_queue.receive_messages(WaitTimeSeconds=20):
                print("Received message from SQS:")
                print(message.body)

                # Break the loop
                if message.body == "quit":
                    running = False
                    break

                # Parse config
                config = json.loads(message.body)
                print(config)

                # Start/update pipeline
                result = client.schedule(config)

                # Send the response
                push_queue.send_message(
                    MessageBody=json.dumps(result),
                    MessageAttributes={
                        'InputMessageId': {
                            'StringValue': message.message_id,
                            'DataType': 'String'
                        }
                    }
                )

                # Let the queue know that the message is processed
                message.delete()
        except Exception as e:
            print("Failed to configure pipeline(s): " + repr(e))

        time.sleep(3)

    # Delete queue(s)
    pull_queue.delete()
    push_queue.delete()

    print("All done.")
