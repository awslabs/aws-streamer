
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

def get_python_plugins_list():
    '''
    Returns list of python plug-ins
    '''
    root_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    python_plugins_dir = os.path.join(root_path, "gst_plugins", "python")

    python_plugins = []
    for f in os.listdir(python_plugins_dir):
        if f == "__init__.py":
            continue
        if f.endswith(".py"):
            python_plugins.append(os.path.splitext(f)[0])

    return python_plugins
