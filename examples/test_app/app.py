
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import argparse
import awstreamer

dir_path = os.path.abspath(os.path.dirname(__file__))
cwd = os.getcwd()

if __name__ == "__main__":
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=str, nargs='?', default="config.json", help="Configuration file")
    args = parser.parse_args()
    print(args)

    # Config file name
    if args.config.startswith("/"):
        config_file = args.config
    else:
        config_file = os.path.join(cwd, args.config)
    print(config_file)

    # Start the pipeline
    client = awstreamer.client()
    client.schedule(config_file, wait_for_finish=True)

    print("All done.")
