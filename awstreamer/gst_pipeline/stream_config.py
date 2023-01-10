#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging
import json
import csv
import collections

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class StreamConfig(dict):

    DEFAULT_CONFIG_FILE = "config.json"
    DEFAULT_CLASSES_FILE = "classes.csv"

    def __init__(self, *args, **kwargs):
        # Default params
        self.update({
            "id": "default",
            "enabled": True,
            "debug": True,
            "info": None,
            "pipeline": {}, # string in dotted format or dict
            "callback": None,
            "timeout": None,
            "source": None,
            "env": None
        })

        # Overwrite all default params with the input ones
        if (len(args) > 0):
            self.update(StreamConfig.DeepUpdate(self, args[0]))

        # Set default source to test source
        if self["source"] is None:
            self["source"] = {
                "name": "videotestsrc",
                "is-live": True,
                "do-timestamp": True
            }

    @staticmethod
    def DeepUpdate(original, update):
        '''
        Recursively update a dict. Subdicts won't be overwritten but also updated.
        '''
        if not isinstance(original, collections.abc.Mapping):
            return update
        for key, value in update.items():
            if isinstance(value, collections.abc.Mapping):
                original[key] = StreamConfig.DeepUpdate(original.get(key), value)
            else:
                original[key] = value
        return original

    @staticmethod
    def LoadJSON(filename):
        with open(filename) as json_file:
            return json.load(json_file, object_pairs_hook=collections.OrderedDict)

    @staticmethod
    def LoadCSV(filename):
        with open(filename) as csvfile:
            return dict(filter(None, csv.reader(csvfile, delimiter=',')))

    @staticmethod
    def LoadConfigFromFile(filename=None, try_cwd=True):
        if filename is None:
            filename = StreamConfig.DEFAULT_CONFIG_FILE

        if os.path.exists(filename):
            logger.info("Loading config from file: %s" % filename)
            return StreamConfig.LoadJSON(filename)
        else:
            logger.error("File not found: %s" % filename)

        if try_cwd:
            # Let's append to current working directory and try again
            return StreamConfig.LoadConfigFromFile(os.path.join(os.getcwd(), filename), try_cwd=False)

        return dict()

    @staticmethod
    def __get(obj, key):
        if type(key) is str:
            chain = key.split('.')
        else:
            chain = key
        _key = chain.pop(0)
        if _key in obj:
            return StreamConfig.__get(obj[_key], chain) if chain else obj[_key]
        return None

    def get(self, key):
        return StreamConfig.__get(self, key)

    def isSet(self, key):
        found = self.get(key)
        return found is not None
