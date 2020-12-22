#!/bin/bash

SOURCE_DIR=$1
FUNCTION_NAME=$2
RUNTIME=$3
PROFILE=$4
REGION=$5
ROLE=$6

if [ "$#" -lt 4 ]; then
    PROFILE=default
fi

if [ "$#" -lt 5 ]; then
    REGION=`aws configure get $PROFILE.region --output text`
fi

# Check if function exists
FUNCTION_ARN=`aws lambda list-functions --query "Functions[?FunctionName=='$FUNCTION_NAME'].FunctionArn" --output text --profile ${PROFILE}`

if [ "$#" -lt 6 ]; then
    if [[ "$FUNCTION_ARN" == "" ]]; then
        aws iam create-role --role-name Lambda_empty --profile ${PROFILE} --assume-role-policy '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                "Action": "sts:AssumeRole"
                }
            ]
        }'
        ROLE=`aws iam list-roles --query "Roles[?RoleName=='Lambda_empty'].Arn" --output text --profile ${PROFILE}`
    fi
fi

cd ${SOURCE_DIR}
    rm -rf *.zip
    rm -rf __pycache__
    zip -r ${FUNCTION_NAME}.zip *

    if [[ "$FUNCTION_ARN" == "" ]]; then
        echo "First time publishing..."

        export VERSION=$(aws lambda create-function \
            --region $REGION \
            --profile ${PROFILE} \
            --function-name $FUNCTION_NAME \
            --handler lambda_function.lambda_handler \
            --role $ROLE \
            --zip-file fileb://$FUNCTION_NAME.zip \
            --runtime $RUNTIME \
            --publish | tee /dev/tty | jq -r ".Version")

        echo "Version: $VERSION"

        aws lambda create-alias \
            --function-name $FUNCTION_NAME \
            --name GG_ALIAS \
            --function-version $VERSION \
            --region $REGION \
            --profile ${PROFILE}

        aws lambda publish-version \
            --function-name $FUNCTION_NAME \
            --region $REGION \
            --profile ${PROFILE}

    else

        echo "Updating lambda function..."

        export VERSION=$(aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --zip-file fileb://${FUNCTION_NAME}.zip \
            --region $REGION \
            --profile ${PROFILE} \
            --publish | tee /dev/tty | jq -r ".Version")

        echo "Version: $VERSION"

        aws lambda update-alias \
            --region $REGION \
            --profile ${PROFILE} \
            --function-name $FUNCTION_NAME \
            --name GG_ALIAS \
            --function-version $VERSION
    fi
cd ..
