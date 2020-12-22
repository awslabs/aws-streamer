#!/bin/bash

SOURCE_DIR=$1
FUNCTION_NAME=$2
RESTART_GG=$3

if [ "$#" -ne 3 ]; then
    RESTART_GG=ON
fi

if [[ "$RESTART_GG" == "ON" ]]; then
    sudo /greengrass/ggc/core/greengrassd stop
fi

# Find full function name
echo $FUNCTION_NAME
cd /greengrass/ggc/deployment/lambda/
    pattern=$FUNCTION_NAME
    for _dir in *"${pattern}"*; do
        [ -d "${_dir}" ] && dir="${_dir}" && break
    done
    echo "${dir}"
cd ..

dst_path=/greengrass/ggc/deployment/lambda/${dir}/

echo "Copying from ${SOURCE_DIR} to $dst_path"
sudo cp -r ${SOURCE_DIR}/* $dst_path
sudo ls -la $dst_path

if [[ "$RESTART_GG" == "ON" ]]; then
    sudo /greengrass/ggc/core/greengrassd start
fi
