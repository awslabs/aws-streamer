
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from awstreamer.utils.video import get_video_files_in_time_range, merge_video_files

if __name__ == '__main__':

    file_list = get_video_files_in_time_range(
        path = "/video/camera_0/",
        timestamp_from = "2020-08-05 13:03:47",
        timestamp_to = "2020-08-05 13:05:40",
    )

    merged = merge_video_files(
        files = file_list,
        destination_file = "merged.mkv"
    )

    print("Merged file info: " + str(merged))