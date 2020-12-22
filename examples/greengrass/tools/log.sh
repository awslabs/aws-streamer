#!/bin/bash

FUNCTION_NAME=$1
USER=707132582539
REGION=ap-southeast-1

if [[ "$FUNCTION_NAME" == "runtime" ]]; then
    tail -F /greengrass/ggc/var/log/system/runtime.log

else
    cd /greengrass/ggc/var/log/user/$REGION/$USER
        # Find log file with function name in it
        pattern=$FUNCTION_NAME
        for _file in *"${pattern}"*; do
            file="${_file}" && break
        done
        echo "${file}"

        # Print log
        tail -F $file
    cd ..
fi