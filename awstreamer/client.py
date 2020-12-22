
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

def client(client_type="pipeline", *args, **kwargs):
    if client_type == "configurer":
        from .gst_configurer.configurer_client import ConfigurerClient as Client
    elif client_type == "viewer":
        from .gst_viewer.viewer_client import ViewerClient as Client
    elif client_type == "pipeline":
        from .gst_pipeline.stream_client import StreamClient as Client
    else:
        raise Exception('Client type {} is not recognized.'.format(repr(client_type)))

    return Client(*args, **kwargs)
