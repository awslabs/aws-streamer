from __future__ import print_function
from crhelper import CfnResource
import logging
import boto3
import os
import sys
import json
from botocore.exceptions import ClientError
logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
# Initialise the helper, all inputs are optional, this example shows the defaults
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

c = boto3.client('greengrass')
iam = boto3.client('iam')

try:
    ## Init code goes here
    pass
except Exception as e:
    helper.init_failure(e)


def find_group(thingName):
    response_auth = ''

    response = c.list_groups()
    for group in response['Groups']:
        thingfound = False
        group_version = c.get_group_version(
            GroupId=group['Id'],
            GroupVersionId=group['LatestVersion']
        )
        
        core_arn = group_version['Definition'].get('CoreDefinitionVersionArn', '')
        if core_arn:
            core_id = core_arn[core_arn.index('/cores/')+7:core_arn.index('/versions/')]
            core_version_id = core_arn[core_arn.index('/versions/')+10:len(core_arn)]
            thingfound = False
            response_core_version = c.get_core_definition_version(
                CoreDefinitionId=core_id,
                CoreDefinitionVersionId=core_version_id
            )
            if 'Cores' in response_core_version['Definition']:
                for thing_arn in response_core_version['Definition']['Cores']:
                    if thingName == thing_arn['ThingArn'].split('/')[1]:
                        thingfound = True
                        break
        if(thingfound):
            logger.info('found thing: %s, group id is: %s' % (thingName, group['Id']))
            response_auth = group['Id']
            return(response_auth)


def manage_greengrass_role(cmd):

    role_arn = os.environ['ROLE_ARN']

    if cmd == 'CREATE':
        c.associate_service_role_to_account(RoleArn=role_arn)
        logger.info('Associated role {}'.format(role_arn))
    else:
        try:
            c.disassociate_service_role_from_account()
            logger.info('Disassociated role {}'.format(role_arn))
        except ClientError:
            return


@helper.create
def create(event, context):
    logger.info("Got Create")

    manage_greengrass_role('CREATE')
    logger.info('Greengrass service role associated')


@helper.update
def update(event, context):
    logger.info("Got Update")
    # If the update resulted in a new resource being created, return an id for the new resource. 
    # CloudFormation will send a delete event with the old id when stack update completes


@helper.delete
def delete(event, context):
    logger.info("Got Delete")
    thingName=event['ResourceProperties']['ThingName']
    
    group_id = find_group(thingName)
    logger.info('Group id to delete: %s' % group_id)
    if group_id:
        c.reset_deployments(
            Force=True,
            GroupId=group_id
        )
        logger.info('Forced reset of Greengrass deployment')
        manage_greengrass_role('DELETE')
    else:
        logger.error('No group Id for thing: %s found' % thingName)


def handler(event, context):
    logger.info('Received event: {}'.format(json.dumps(event)))
    helper(event, context)