#!/bin/bash

BUCKET_NAME=$1

# Get bootstrap file from S3
aws s3 cp s3://$BUCKET_NAME/bootstrap.json .

# Stop greengrass
sudo /greengrass/ggc/core/greengrassd stop

# Modify local certs
cat bootstrap.json | jq -r '.certificatePem' > core.cert.pem
cat bootstrap.json | jq -r '.keyPair.PrivateKey' > core.private.key
cat bootstrap.json | jq -r '.configFile' > config.json
sudo mv core.cert.pem /greengrass/certs/
sudo mv core.private.key /greengrass/certs/
sudo mv config.json /greengrass/config/
rm bootstrap.json

# Get public certificate
sudo wget https://www.amazontrust.com/repository/AmazonRootCA1.pem -O /greengrass/certs/root.ca.pem

# Restart greengrass
sudo /greengrass/ggc/core/greengrassd start
