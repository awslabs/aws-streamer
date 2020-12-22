#!/bin/bash

full_path=$(realpath $0)
dir_path=$(dirname $full_path)/

cd ${dir_path}
    # --------------------------------------
    # AWS Greengrass SDK
    # --------------------------------------
    if [ ! -d aws-greengrass-core-sdk-python ]; then
        git clone --depth 1 https://github.com/aws/aws-greengrass-core-sdk-python.git
    fi

    GREENGRASS_SDK=${dir_path}aws-greengrass-core-sdk-python/greengrasssdk
    cp -r $GREENGRASS_SDK ../src/gstreamer_pipeline/
    cp -r $GREENGRASS_SDK ../src/data_uploader/
    cp -r $GREENGRASS_SDK ../src/viewer/

    # --------------------------------------
    # AWS Streamer
    # --------------------------------------
    AWS_GST_SDK=${dir_path}../aws-gst-sdk
    $AWS_GST_SDK/build.sh -DBUILD_KVS=ON

    rm -rf ../src/gstreamer_pipeline/awstreamer
    rm -rf ../src/data_uploader/awstreamer
    rm -rf ../src/viewer/awstreamer

    cp -r $AWS_GST_SDK/build/awstreamer_py ../src/gstreamer_pipeline/awstreamer
    cp -r $AWS_GST_SDK/build/awstreamer_py ../src/data_uploader/awstreamer
    cp -r $AWS_GST_SDK/build/awstreamer_py ../src/viewer/awstreamer

    # --------------------------------------
    # Configs for viewer lambda
    # --------------------------------------
    if [ ! -d ../src/viewer/examples ]; then
        mkdir -p ../src/viewer/examples/requests
    fi
    cp -r $AWS_GST_SDK/examples/configs ../src/viewer/examples/
    cp ../src/data_uploader/request.json ../src/viewer/examples/requests/
    cp ../src/gstreamer_pipeline/config.json ../src/viewer/examples/configs/

    # --------------------------------------
    # Nvidia DeepStream
    # --------------------------------------
    cp -r $AWS_GST_SDK/examples/deepstream/nvinfer_config.txt ../src/gstreamer_pipeline/
    cp -r $AWS_GST_SDK/examples/deepstream/nvinfer_config.txt ../src/viewer/examples/configs/

cd ..
