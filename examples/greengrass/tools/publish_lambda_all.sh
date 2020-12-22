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

full_path=$(realpath $0)
dir_path=$(dirname $full_path)/

# Download AWS SDKs used by lambdas
${dir_path}get_awssdk.sh

# Publish lambdas
${dir_path}publish_lambda.sh ${dir_path}../gstreamer_pipeline gstreamer_pipeline python3.7 ${PROFILE} ${REGION} ${ROLE}
${dir_path}publish_lambda.sh ${dir_path}../data_uploader data_uploader python3.7 ${PROFILE} ${REGION} ${ROLE}
${dir_path}publish_lambda.sh ${dir_path}../viewer viewer python3.7 ${PROFILE} ${REGION} ${ROLE}
