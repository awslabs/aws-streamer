#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import requests
import logging

# Create a global logger
logging.basicConfig(stream=sys.stdout, level=logging.CRITICAL)
logger = logging.getLogger(__name__)

def is_greengrass_enabled():
    for envvar in os.environ:
        if envvar == 'AWS_GG_MQTT_ENDPOINT':
            return True
        elif envvar == 'AWS_GG_HTTP_ENDPOINT':
            return True
        elif envvar == 'AWS_GG_MQTT_PORT':
            return True
    return False

def is_ecs_enabled():
    for envvar in os.environ:
        if envvar == 'ECS_CONTAINER_METADATA_URI':
            return True
    return False

def get_aws_credentials():
    '''
    Gets credentials from the local credential provider
    '''
    accessKeyId = str()
    secretAccessKey = str()
    token = str()

    try:
        # Get credentials from the local credential provider
        serviceUrl = os.environ["AWS_CONTAINER_CREDENTIALS_FULL_URI"]
        ggAuthToken = os.environ["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        headers = { 'Authorization': ggAuthToken }
        response = requests.get(serviceUrl, headers=headers)
        logger.info(response)

        # Parse values from the response
        responseJson = response.json()
        accessKeyId = responseJson['AccessKeyId']
        secretAccessKey = responseJson['SecretAccessKey']
        token = responseJson['Token']
    except Exception as e:
        logger.error("Failed to set AWS credentials: " + repr(e))

    return accessKeyId, secretAccessKey, token

def get_aws_credentials_boto3():
    '''
    Gets credentials from boto3 session
    '''
    accessKeyId = str()
    secretAccessKey = str()
    token = str()

    try:
        import boto3
        session = boto3.Session()
        credentials = session.get_credentials()

        # Credentials are refreshable, so accessing your access key / secret key
        # separately can lead to a race condition. Use this to get an actual matched
        # set.
        credentials = credentials.get_frozen_credentials()
        accessKeyId = credentials.access_key
        secretAccessKey = credentials.secret_key
        token = credentials.token
    except Exception as e:
        logger.error("Failed to set AWS credentials: " + repr(e))

    return accessKeyId, secretAccessKey, token

def try_get_aws_credentials():
    '''
    Try to obtain AWS credentials
    '''
    if is_greengrass_enabled():
        return get_aws_credentials()
    else:
        return get_aws_credentials_boto3()

def set_aws_env_variables():
    '''
    Sets AWS environmental variables from the local credential provider
    '''
    logger.info("Setting AWS env variables...")
    logger.info(os.environ)
    if is_greengrass_enabled() or is_ecs_enabled():
        if is_greengrass_enabled():
            accessKeyId, secretAccessKey, token = get_aws_credentials()
        else:
            accessKeyId, secretAccessKey, token = get_aws_credentials_boto3()

        # Set AWS env variables
        os.environ['AWS_ACCESS_KEY_ID'] = accessKeyId
        os.environ['AWS_SECRET_ACCESS_KEY'] = secretAccessKey
        os.environ['AWS_SESSION_TOKEN'] = token

    if 'AWS_REGION' in os.environ:
        os.environ['AWS_DEFAULT_REGION'] = os.environ['AWS_REGION']

    logger.info(os.environ)

def get_aws_plugins_list():
    '''
    Returns list of AWS plug-ins
    '''
    AWS_PLUGINS = [ "kvssink", "s3sink" ]
    return AWS_PLUGINS
