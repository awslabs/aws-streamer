#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from flask import render_template, Flask, send_from_directory, request, jsonify
import os
from os import listdir
from os.path import isfile, join
import json
import requests
import io
import boto3
from time import sleep
from pprint import pformat

from ..utils.aws import try_get_aws_credentials

s3 = boto3.client('s3')
sqs = boto3.resource('sqs')
app = Flask(__name__)

VIDEO_VOLUME_PATH = os.environ['VIDEO_VOLUME_PATH'] if 'VIDEO_VOLUME_PATH' in os.environ else "/video"
VIDEO_BUCKET_NAME = os.environ['VIDEO_BUCKET_NAME'] if 'VIDEO_BUCKET_NAME' in os.environ else ""
THING_NAME = os.environ['THING_NAME'] if 'THING_NAME' in os.environ else ""
API_GATEWAY_URL = os.environ['API_GATEWAY_URL'] if 'API_GATEWAY_URL' in os.environ else ""
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ACCESS_TOKEN = try_get_aws_credentials()
AWS_REGION = os.environ['AWS_DEFAULT_REGION'] if 'AWS_DEFAULT_REGION' in os.environ else "us-west-2"

@app.after_request
def add_header(response):
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def send_request(topic, message, url):
    payload = {
        "topic": topic,
        "message": message
    }
    headers = {
        'Content-Type': 'application/json',
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()

def send_request_serverless(queue_name, message, url):
    streamingAction = "config"
    taskId = ""
    if "ecs" in message:
        streamingAction = message["ecs"]["taskAction"]
        if streamingAction == "stop":
            taskId = message["ecs"]["taskArn"]
        del message["ecs"]

    params = {
        "streamingAction": streamingAction,
        "queueName": queue_name,
        "taskId": taskId
    }
    headers = {
        'Content-Type': 'application/json',
    }
    response = requests.post(url, headers=headers, params=params, data=json.dumps(message))

    if streamingAction == "start":
        return { "TaskArn": response.json() }
    else:
        return response.json()

def get_response_from_s3(bucket, group):
    status = dict()
    try:
        key = group + ".log"
        buffer = io.BytesIO()
        s3.download_fileobj(Bucket=bucket, Key=key, Fileobj=buffer)
        byte_value = buffer.getvalue()
        str_value = byte_value.decode()
        status = json.loads(str_value)
    except Exception as e:
        print(repr(e))
    return status

def get_response_from_sqs(queue_name):
    status = None
    try:
        # Get the queue
        res_queue_name = queue_name + "-res"
        queue = sqs.get_queue_by_name(QueueName=res_queue_name)

        # Crunch all messages and leave the status of the last one
        for message in queue.receive_messages():
            print("Received message from SQS:")
            print(message.body)
            status = json.loads(message.body)
            message.delete()
    except Exception as e:
        print(repr(e))
    return status

def publish(url, group, topic, message, bucket):
    # Send request
    response = send_request(topic, message, url)

    # Get a response file from S3
    if response["statusCode"] == 200:
        return get_response_from_s3(bucket, group)
    return dict()

def publish_serverless(url, queue_name, message):
    # Send request
    response = send_request_serverless(queue_name, message, url)
    print(pformat(response))

    # Get a response file from SQS
    if isinstance(response, str):
        return { "Response": response }
    elif "statusCode" in response and response["statusCode"] == 200:
        return get_response_from_sqs(queue_name)
    elif isinstance(response, dict):
        return response
    return dict()

def list_files(path):
    if os.path.exists(path):
        return { f: join(path, f) for f in listdir(path) if isfile(join(path, f))}
    return dict()

def get_configs_from_path(path):
    d = {
        "configs": list_files(os.path.join(path, "configs")),
        "requests": list_files(os.path.join(path, "requests"))
    }
    return d

def get_configs():
    cwd_path = os.getcwd()
    file_path = os.path.abspath(os.path.dirname(__file__))
    # Try 2, 3 and 4 levels up
    d = get_configs_from_path(os.path.join(file_path, "../../examples/"))
    if len(d["configs"].keys()) == 0:
        d = get_configs_from_path(os.path.join(file_path, "../../../examples/"))
    if len(d["configs"].keys()) == 0:
        d = get_configs_from_path(os.path.join(file_path, "../../../../examples/"))
    return d

@app.route('/')
def index():
    return render_template('index.html', \
        configs = get_configs(), \
        videoVolumePath = VIDEO_VOLUME_PATH, \
        videoBucketPath = VIDEO_BUCKET_NAME, \
        thingName = THING_NAME, \
        apiGatewayUrl = API_GATEWAY_URL, \
        accessKeyId = AWS_ACCESS_KEY_ID, \
        secretAccessKey = AWS_SECRET_ACCESS_KEY, \
        sessionToken = AWS_ACCESS_TOKEN, \
        awsRegion = AWS_REGION)

@app.route('/publish_message')
def publish_message():
    message = str(request.args.get('message'))
    label = str(request.args.get('label'))
    url = str(request.args.get('url'))
    group_or_queue = str(request.args.get('group_or_queue'))
    bucket = str(request.args.get('bucket'))
    backend = str(request.args.get('backend'))

    if backend == "greengrass":
        # Get IoT topic
        topic = group_or_queue
        if label == "Configs":
            topic += "/config/camera"
        else:
            topic += "/req/data"

        response = publish(url, group_or_queue, topic, json.loads(message), bucket)
    else:
        response = publish_serverless(url, group_or_queue, json.loads(message))
    return jsonify({"result": json.dumps(response)})

@app.route('/get_response')
def get_response():
    backend = str(request.args.get('backend'))
    if backend == "greengrass":
        bucket = str(request.args.get('bucket'))
        group = str(request.args.get('group_or_queue'))
        response = get_response_from_s3(bucket, group)
    else:
        queue = str(request.args.get('group_or_queue'))
        response = get_response_from_sqs(queue)
    return jsonify({"result": json.dumps(response) if response else None})

@app.route('/load_config')
def load_config():
    filepath = str(request.args.get('filepath'))
    if filepath.startswith("./"):
        path = os.path.abspath(os.path.dirname(__file__))
        filepath = filepath.replace("./", os.path.join(path, "templates/"))

    text = str()
    with open(filepath) as file:
        text = file.read()

    return jsonify({"result": text})

@app.route(VIDEO_VOLUME_PATH + '/<string:file_name>')
def stream(file_name):
    return send_from_directory(directory=VIDEO_VOLUME_PATH, filename=file_name)

class ConfigurerClient():
    def __init__(self):
        app.run()

if __name__ == "__main__":
    app.run()
