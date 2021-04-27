import logging
import uuid
import json

import boto3
from crhelper import CfnResource
from tenacity import retry, retry_if_result, wait_fixed

logger = logging.getLogger(__name__)
helper = CfnResource(json_logging=True, log_level='DEBUG',
                     boto_level='DEBUG', sleep_on_delete=120)
try:
    cfn = boto3.client('cloudformation', region_name='us-east-1')
except Exception as e:
    logger.error(e, exc_info=True)
    helper.init_failure(e)


def log_exception(e):
    print(getattr(e, 'message', repr(e)))
    logger.error(e)


@helper.create
def create(event, context):
    logger.info("got CREATE")
    config = {}
    config['StackName'] = event["ResourceProperties"]["Stack"]
    config['TemplateBody'] = json.dumps(
        json.loads(open('./templates/waf.json', 'r').read()))
    config['Capabilities'] = ['CAPABILITY_IAM',
                              'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND']
    config['OnFailure'] = 'DELETE'
    try:
        cfn.create_stack(**config)
        create_wafstack(config['StackName'])
    except Exception as e:
        log_exception(e)
    result = cfn.describe_stacks(StackName=config['StackName'])[
        'Stacks'][0]['Outputs']
    outputs = [({x['OutputKey']:x['OutputValue']}) for x in result]
    for output in outputs:
        helper.Data.update(output)
    return config['StackName']


@helper.update
def create(event, context):
    logger.info("got UPDATE")
    create(event, context)


@helper.delete
def delete(event, context):
    logger.info("got DELETE")
    cfn.delete_stack(StackName=event["PhysicalResourceId"])


def is_created(result):
    return True if result.upper() == "CREATE_IN_PROGRESS" else False


@retry(retry=retry_if_result(is_created), wait=wait_fixed(5))
def create_wafstack(stack_name):
    try:
        status = cfn.describe_stacks(StackName=stack_name)[
            "Stacks"][0]["StackStatus"]
        print(f"{stack_name} creation is {status}")
    except Exception as e:
        log_exception(e)
    return status


def handler(event, context):
    global logger
    helper(event, context)
