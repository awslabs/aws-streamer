
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import platform
import json
import logging
import time
import boto3
import io
from botocore.exceptions import ClientError
import concurrent.futures
from pprint import pformat
from threading import Thread
from functools import wraps
from os.path import isfile, join
import glob
import shutil
import gstaws
from gstaws.utils.aws import is_greengrass_enabled
from gstaws.utils.video import get_video_files_in_time_range, merge_video_files, sec_to_timestamp, list_files, sort_files_by_creation_time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Thread pool
_DEFAULT_POOL = concurrent.futures.ThreadPoolExecutor()

if is_greengrass_enabled():
    import greengrasssdk

def threaded(f, executor=None):
    @wraps(f)
    def wrap(*args, **kwargs):
        return (executor or _DEFAULT_POOL).submit(f, *args, **kwargs)
    return wrap

class DataHandler():
    def __init__(self, config=None):
        logger.info("Initializing DataHandler...")
        if config is not None:
            self.configure(config)

    def configure(self, config):
        logger.info("Configuring DataHandler...")
        self.config = config
        self.ggClient = self.loadGreengrassClient(config)
        self.dirPath = config["dir"]

    def loadGreengrassClient(self, config):
        logger.info("Loading Greengrass client...")

        # Nothing to do if not inside greengrass
        if is_greengrass_enabled():
            return greengrasssdk.client("iot-data")
        return None

    @threaded
    def publishToGreengrass(self, message, topic=None):
        '''
        Publishes to MQTT topic
        '''
        if not self.config["greengrass"]["enabled"]:
            return
        # Get default topic
        if topic is None:
            if self.config["greengrass"]["topic"]:
                topic = self.config["greengrass"]["topic"]
            elif "THING_NAME" in os.environ:
                topic = os.environ['THING_NAME'] + '/data/res'

        # Publish to topic
        if self.ggClient and topic:
            try:
                self.ggClient.publish(topic=topic, queueFullPolicy="AllOrException", payload=message.encode("utf-8"))
            except Exception as e:
                logger.error("Failed to publish message: " + repr(e))

    @threaded
    def uploadFileObjectToS3(self, metadata, bucket_name=None):
        '''
        Uploads file object to S3
        '''
        if not self.config["s3"]["enabled"]:
            return

        # Get default bucket name
        if bucket_name is None and self.bucket_name is not None:
            bucket_name = self.bucket_name

        try:
            key = metadata["fileName"]
            if self.s3_folder is not None and self.s3_folder != "":
                key = self.s3_folder + "/" + key
            logger.info("[s3] Uploading to bucket/key: %s/%s" % (bucket_name, key))

            # Convert image back to jpeg
            base64array = metadata["frame"]
            buffer = base64.b64decode(base64array)

            # Upload to S3
            s3 = boto3.client('s3')
            response = s3.upload_fileobj(io.BytesIO(buffer), bucket_name, key)
            if response:
                logger.info("[s3] Response: %s" % response)
        except ClientError as e:
            logging.error("Error: %s" % e)
        except Exception as e:
            logger.error("Failed to upload to S3: " + repr(e))

    def getS3KeyPath(self, bucket_name, folder_name, file_name):
        '''
        Combines fields into s3://bucket_name/folder_name/file_name
        returns above path and key
        '''
        key = file_name
        if folder_name != "":
            key = folder_name + '/' + key
        s3_path = "s3://%s/%s" % (bucket_name, key)
        return s3_path, key

    @threaded
    def uploadFileToS3(self, file_path, bucket_name, key):
        '''
        Uploads file to S3
        '''
        if not self.config["s3"]["enabled"]:
            return
        try:
            logger.info("Uploading %s to %s/%s" % (file_path, bucket_name, key))
            s3 = boto3.client('s3')
            response = s3.upload_file(file_path, bucket_name, key)
            if response:
                logger.info("[s3] Response: %s" % response)
        except ClientError as e:
            logging.error("Error: %s" % e)
        except Exception as e:
            logger.error("Failed to upload %s to S3: " % (file_path, repr(e)))

    @threaded
    def uploadFilesToS3(self, request):
        '''
        Uploads video files for specified time range for gateway for camera.
        '''
        result = {
            "files": [],
            "request": request
        }

        try:
            logger.info("Request:")
            logger.info(pformat(request))

            # Parse request
            gateway_id = request["gateway_id"]
            camera_id = request["camera_id"]
            prefix = request["prefix"]
            timestamp_from = request["timestamp_from"] if "timestamp_from" in request else None
            timestamp_to = request["timestamp_to"] if "timestamp_to" in request else None
            s3_bucket = request["s3_bucket"]
            s3_folder = request["s3_folder"]

            # Video path
            path = os.path.join(self.dirPath, gateway_id, camera_id)

            # Get list of files within the time range
            files = get_video_files_in_time_range(
                path = path,
                timestamp_from = timestamp_from,
                timestamp_to = timestamp_to,
                prefix = prefix
            )

            if len(files) > 0:
                # Merge video files
                merged = merge_video_files(
                    files = files,
                    destination_file = os.path.join(self.dirPath, gateway_id, camera_id, "merged.mkv")
                )

                # Upload video segments and merged file
                if merged is not None and len(files) > 1:
                    files.append(merged)

                logger.info("Uploading %d files for time segment [%s, %s]" % (len(files), timestamp_from, timestamp_to))
                for file in files:
                    # Upload file to S3
                    s3_path, s3_key = self.getS3KeyPath(s3_bucket, s3_folder, file[1])
                    self.uploadFileToS3(file[0], s3_bucket, s3_key)

                    # Append uploaded files info
                    result["files"].append({
                        "filepath": file[0],
                        "timestamp": sec_to_timestamp(file[2]),
                        "s3_path": s3_path
                    })
            else:
                # Get list of all files in case time range was incorrect
                files = list_files(path, prefix)
                files = sort_files_by_creation_time(files)

                for file in files:
                    result["files"].append({
                        "filepath": file[0],
                        "timestamp": sec_to_timestamp(file[2])
                    })
                result["error"] = "No files found in requested time range. See all available files above."

        except Exception as e:
            logger.error("Failed to upload to S3: " + repr(e))
            result["error"] = "Failed to upload to S3: " + repr(e)

        # Publish to greengrass topic
        logger.info(pformat(result))
        self.publishToGreengrass(json.dumps(result))
