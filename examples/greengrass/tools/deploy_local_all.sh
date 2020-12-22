#!/bin/bash

full_path=$(realpath $0)
dir_path=$(dirname $full_path)/

sudo /greengrass/ggc/core/greengrassd stop

# Download AWS SDKs used by lambdas
${dir_path}get_awssdk.sh

# Copy lambdas code
${dir_path}deploy_local.sh ${dir_path}../src/gstreamer_pipeline gstreamer_pipeline OFF
${dir_path}deploy_local.sh ${dir_path}../src/data_uploader data_uploader OFF
${dir_path}deploy_local.sh ${dir_path}../src/viewer viewer OFF

sudo /greengrass/ggc/core/greengrassd start
