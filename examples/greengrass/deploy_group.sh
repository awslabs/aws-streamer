#!/bin/bash -e

BUCKET_NAME=$1
STACK_NAME=$2
PROFILE_NAME=$3
DEVICE_CORE_PREFIX=DVR
GROUP_NAME=$DEVICE_CORE_PREFIX-$STACK_NAME

if [ "$#" -lt 3 ]; then
    PROFILE_NAME=default
fi

echo '
#########################################
# Deploying GreenGrass Group
#########################################
'
echo "Group name: ${GROUP_NAME}"

GROUP_ID=`aws greengrass list-groups --query "Groups[?Name=='$GROUP_NAME'].Id" --output text --profile ${PROFILE_NAME}`

GROUP_VERSION_ID=`aws greengrass list-group-versions --group-id ${GROUP_ID} --query 'Versions[0].Version' --output text --profile ${PROFILE_NAME}`

aws greengrass create-deployment --group-id ${GROUP_ID} --group-version-id "${GROUP_VERSION_ID}" --deployment-type NewDeployment --profile ${PROFILE_NAME}
