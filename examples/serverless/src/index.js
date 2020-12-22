// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

'use strict';

var AWS = require('aws-sdk');
var ecs = new AWS.ECS();
var sqs = new AWS.SQS();

// Reading environment variables
const ecsClusterArn = process.env.ecsClusterArn;
const ecsTaskDefinitionArn = process.env.ecsTaskDefinitionArn;
const ecsContainerName = process.env.ecsContainerName;
const ecsSecurityGroup = process.env.ecsSecurityGroup;
const ecsSubnet1 = process.env.ecsSubnet1;
const ecsSubnet2 = process.env.ecsSubnet2;

let responseBody = {
    message: '',
    input: ''
};

let response = {
    statusCode: 200,
    headers: {},
    body: ''
};

exports.handler = function(event, context, callback) {
    let taskId = "";
    let streamingAction = "";
    let queueName = "";

    console.log(event);
    responseBody.input = event;

    if (event.queryStringParameters && event.queryStringParameters.streamingAction) {
        console.log("Streaming action: " + event.queryStringParameters.streamingAction);
        streamingAction = event.queryStringParameters.streamingAction;
    }

    switch(streamingAction.toLowerCase()) {
        case 'start':
            if (event.queryStringParameters && event.queryStringParameters.queueName) {
                console.log("SQS Queue Name: " + event.queryStringParameters.queueName);
                queueName = event.queryStringParameters.queueName;
                return startTask(event, context, queueName);
            } else {
                responseBody = {
                    message: "Missing parameter: queueName",
                    input: event
                };
                response = {
                    statusCode: 400,
                    headers: {},
                    body: JSON.stringify(responseBody, null, ' ')
                };
                context.succeed(response);
            }
        case 'config':
            if (event.queryStringParameters && event.queryStringParameters.queueName) {
                console.log("SQS Queue Name: " + event.queryStringParameters.queueName);
                queueName = event.queryStringParameters.queueName;
                return configureStream(event, context, queueName);
            } else {
                responseBody = {
                    message: "Missing parameter: queueName",
                    input: event
                };
                response = {
                    statusCode: 400,
                    headers: {},
                    body: JSON.stringify(responseBody, null, ' ')
                };
                context.succeed(response);
            }
        case 'stop':
            if (event.queryStringParameters && event.queryStringParameters.taskId && event.queryStringParameters.queueName) {
                console.log("ECS task ID: " + event.queryStringParameters.taskId);
                taskId = event.queryStringParameters.taskId;
                console.log("SQS Queue Name: " + event.queryStringParameters.queueName);
                queueName = event.queryStringParameters.queueName;
                return stopTask(event, context, taskId, queueName);
            } else {
                responseBody = {
                    message: "Missing parameter: taskId or queueName",
                    input: event
                };
                response = {
                    statusCode: 400,
                    headers: {},
                    body: JSON.stringify(responseBody, null, ' ')
                };
                context.succeed(response);
            }
        default:
            responseBody = {
                message: "Invalid parameter: streamingAction. Valid values 'start', 'config' & 'stop'",
                input: event
            };
            response = {
                statusCode: 400,
                headers: {},
                body: JSON.stringify(responseBody)
            };
    }

    console.log("response: " + JSON.stringify(response));
    callback(null, response);
};

function startTask(event, context, queueName) {
    let ecsRunTaskParams = {
        cluster: ecsClusterArn,
        launchType: "FARGATE",
        count: 1,
        networkConfiguration: {
           'awsvpcConfiguration': {
                'subnets': [ ecsSubnet1, ecsSubnet2 ],
                'securityGroups': [ ecsSecurityGroup ],
                'assignPublicIp': "ENABLED"
            }
        },
        overrides: {
            containerOverrides: [
                 {
                    environment: [
                        {
                            name: "CONFIG_BODY",
                            value: event.body
                        },
                        {
                            name: "QUEUE_NAME",
                            value: queueName
                        }
                    ],
                    name: ecsContainerName
                }
            ],
        },
        taskDefinition: ecsTaskDefinitionArn
    };

    ecs.runTask(ecsRunTaskParams, function(err, data) {
        if (err) {
            console.log(err);   // an error occurred
            response.statusCode = err.statusCode;
            response.body = JSON.stringify(err, null, ' ');
            context.succeed(response);
        } else {
            console.log(data);  // successful response
            response.statusCode = 200;
            response.body = JSON.stringify((data.tasks.length && data.tasks[0].taskArn) ? data.tasks[0].taskArn : data, null, ' ');
            context.succeed(response);
        }
    });
}

function configureStream(event, context, queueName) {
    var getQueueUrlParams = {
      QueueName: queueName
    };
    sqs.getQueueUrl(getQueueUrlParams, function(err, data) {
        if (err) {
            console.log(err);   // an error occurred
            response.statusCode = err.statusCode;
            response.body = JSON.stringify(err, null, ' ');
            context.succeed(response);
        } else {
            console.log("Success", data.QueueUrl);
            var sendMessageParams = {
                MessageBody: event.body,
                QueueUrl: data.QueueUrl
            };
            sqs.sendMessage(sendMessageParams, function(err, data) {
                if (err) {
                    console.log(err);   // an error occurred
                    response.statusCode = err.statusCode;
                    response.body = JSON.stringify(err, null, ' ');
                    context.succeed(response);
                } else {
                    console.log(data);  // successful response
                    response.statusCode = 200;
                    response.body = JSON.stringify(data, null, ' ');
                    context.succeed(response);
                }
            });
        }
    });
}

function sleep(millis) {
    return new Promise(resolve => setTimeout(resolve, millis));
}

function stopTask(event, context, taskId, queueName) {
    // Gracefully kill the task
    event.body = "quit";
    configureStream(event, context, queueName);
    sleep(3 * 1000);

    // Stop the task
    let ecsStopTaskParam = {
        cluster: ecsClusterArn,
        task: taskId
    };
    ecs.stopTask(ecsStopTaskParam, function(err, data) {
        if (err) {
            console.log(err);   // an error occurred
            response.statusCode = err.statusCode;
            response.body = JSON.stringify(err, null, ' ');
            context.succeed(response);
        } else {
            console.log(data);  // successful response
            response.statusCode = 200;
            responseBody = data;
            response.body = JSON.stringify(data, null, ' ');
            console.log("Stop task succeeded.", response);
            context.succeed(response);
        }
    });
}
