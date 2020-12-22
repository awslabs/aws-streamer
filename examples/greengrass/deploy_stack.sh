#!/bin/bash

BUCKET_NAME=$1
STACK_NAME=$2
PROFILE_NAME=$3

if [ "$#" -lt 3 ]; then
    PROFILE_NAME=default
fi

echo '
###############################
# Publishing lambda functions
###############################
'

GSTREAMER_FUNCTION_NAME=gstreamer_pipeline
GSTREAMER_FUNCTION_ARN=`aws lambda list-functions --query "Functions[?FunctionName=='${GSTREAMER_FUNCTION_NAME}'].FunctionArn" --output text --profile ${PROFILE_NAME}`
echo "${GSTREAMER_FUNCTION_NAME}: ${GSTREAMER_FUNCTION_ARN}"
if [[ "${GSTREAMER_FUNCTION_ARN}" == "" ]]; then
    echo "Failed to find ${GSTREAMER_FUNCTION_NAME} lambda function. Please run tools/publish_lambda_all.sh first"
    exit 1
fi

DATA_UPLOADER_FUNCTION_NAME=data_uploader
DATA_UPLOADER_FUNCTION_ARN=`aws lambda list-functions --query "Functions[?FunctionName=='${DATA_UPLOADER_FUNCTION_NAME}'].FunctionArn" --output text --profile ${PROFILE_NAME}`
echo "${DATA_UPLOADER_FUNCTION_NAME}: ${DATA_UPLOADER_FUNCTION_ARN}"
if [[ "${DATA_UPLOADER_FUNCTION_ARN}" == "" ]]; then
    echo "Failed to find ${DATA_UPLOADER_FUNCTION_NAME} lambda function. Please run tools/publish_lambda_all.sh first"
    exit 1
fi

VIEWER_FUNCTION_NAME=viewer
VIEWER_FUNCTION_ARN=`aws lambda list-functions --query "Functions[?FunctionName=='${VIEWER_FUNCTION_NAME}'].FunctionArn" --output text --profile ${PROFILE_NAME}`
echo "${VIEWER_FUNCTION_NAME}: ${VIEWER_FUNCTION_ARN}"
if [[ "${VIEWER_FUNCTION_ARN}" == "" ]]; then
    echo "Failed to find ${VIEWER_FUNCTION_NAME} lambda function. Please run tools/publish_lambda_all.sh first"
    exit 1
fi

echo '
###############################
# Building and deploying Stack
###############################
'

sam build -t cloudformation.yml --profile ${PROFILE_NAME}

sam package \
    --output-template-file packaged.yml \
    --s3-bucket ${BUCKET_NAME} \
    --profile ${PROFILE_NAME}

aws cloudformation deploy --template-file packaged.yml \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
    --parameter-overrides \
        FunctionArnList="${GSTREAMER_FUNCTION_ARN}:GG_ALIAS,${DATA_UPLOADER_FUNCTION_ARN}:GG_ALIAS,${VIEWER_FUNCTION_ARN}:GG_ALIAS" \
    --profile ${PROFILE_NAME}
