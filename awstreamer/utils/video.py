#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from os import listdir
from os.path import isfile, join
import platform
import json
import logging
import time
from pathlib import Path
from pprint import pformat

from ..client import client

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime

def list_files(path, prefix=""):
    '''
    List all files in the path.
    Returns list of tuples: (full_path, file_name, creation_time)
    '''
    filelist = [f for f in listdir(path) if isfile(join(path, f))]
    filelist = [(join(path, f), f, creation_date(join(path, f))) for f in filelist if f.startswith(prefix)]
    return filelist

def sort_files_by_creation_time(filelist):
    '''
    Sorts files by creation time
    '''
    return sorted(filelist, key=lambda x: x[2], reverse=False)

def timestamp_to_tuple(timestamp):
    '''
    timestamp: YYYY-MM-DD HH:mm:ss in local time
    return tuple
    '''
    date, time = timestamp.split(' ')
    year, month, day = date.split('-')
    hour, minute, second = time.split(':')
    return (int(year), int(month), int(day), int(hour), int(minute), int(second), 0, 0, -1)

def timestamp_to_sec(timestamp):
    '''
    timestamp: YYYY-MM-DD HH:mm:ss in local time
    returns seconds
    '''
    return time.mktime(timestamp_to_tuple(timestamp))

def sec_to_timestamp(sec):
    '''
    Does opposite of timestampToSec()
    '''
    return time.asctime(time.localtime(sec))

def select_files_in_time_range(files, timestamp_from, timestamp_to):
    '''
    Selects files in the specifed time range
    '''
    # Parse time stamp
    try:
        sec_from = timestamp_to_sec(timestamp_from)
        sec_to = timestamp_to_sec(timestamp_to)
    except:
        return []

    logger.info("sec_from: %s" % sec_from)
    logger.info("sec_to: %s" % sec_to)

    selectedFiles = []
    idx_from = -1
    idx_to = -1
    for i in range(len(files)):
        timestamp = files[i][2]

        # Find start time
        if idx_from < 0 and timestamp > sec_from:
            idx_from = i - 1

        # Append files if start time has been found
        if idx_from >= 0:
            selectedFiles.append(files[i - 1])

        # Find end time
        if idx_to < 0 and timestamp >= sec_to:
            idx_to = i
            break

    logger.info("idx_from: %d" % idx_from)
    logger.info("idx_to: %d" % idx_to)

    return selectedFiles

def get_video_files_in_time_range(path, timestamp_from, timestamp_to, prefix=""):
    # List video files in the path
    files = list_files(path, prefix)

    # Sort files by creation time
    files = sort_files_by_creation_time(files)

    # Select files in time range
    files = select_files_in_time_range(files, timestamp_from, timestamp_to)
    logger.info("Selected files: %s" % pformat(files))

    return files

def callback(plugin, file_list):
    return file_list

def merge_video_files(files, destination_file):
    '''
    Returns merged file on success, otherwise None.
    '''
    # Nothing to do
    if len(files) <= 1:
        logger.info("Nothing to merge. Returning file: %s" % files)
        return files[0] if len(files) == 1 else None

    # Make list of full path components
    file_list = [i[0] for i in files]

    # Merge video files
    client().start({
        "pipeline": {
            "source": "splitmuxsrc",
            "parse": "h264parse",
            "mux": "matroskamux",
            "sink": "filesink"
        },
        "source": {
            "linkable": False,
            "signals": {
                "format-location": [callback, file_list]
            }
        },
        "sink": {
            "location": destination_file
        }
    })

    # Return merged file info
    if os.path.isfile(destination_file):
        dst_file = (destination_file, Path(destination_file).name, files[0][2])
        return dst_file

    return None
