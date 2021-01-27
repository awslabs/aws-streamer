#!/bin/bash

PROFILE=$1
REGION=$2
ROLE=$3

if [ "$#" -lt 1 ]; then
    PROFILE=default
fi

if [ "$#" -lt 2 ]; then
    REGION=`aws configure get $PROFILE.region --output text`
fi

RUNTIME=python$(python3 -c 'import sys; print("%d.%d" % (sys.version_info.major, sys.version_info.minor))' 2>&1)

full_path=$(realpath $0)
dir_path=$(dirname $full_path)/

# Download AWS SDKs used by lambdas
${dir_path}get_awssdk.sh

# Publish lambdas
${dir_path}publish_lambda.sh ${dir_path}../gstreamer_pipeline gstreamer_pipeline ${RUNTIME} ${PROFILE} ${REGION} ${ROLE}
${dir_path}publish_lambda.sh ${dir_path}../data_uploader data_uploader ${RUNTIME} ${PROFILE} ${REGION} ${ROLE}
${dir_path}publish_lambda.sh ${dir_path}../viewer viewer ${RUNTIME} ${PROFILE} ${REGION} ${ROLE}
