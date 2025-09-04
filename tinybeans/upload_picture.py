import functools
from pathlib import Path
import typing
import uuid

import boto3
import botocore.config

from . import websiteconfig


@functools.cache
def authenticated_aws_session() -> boto3.Session:
    aws_config = botocore.config.Config(
        region_name = websiteconfig.aws_region,
    )

    aws_cognito_client = boto3.client('cognito-identity', config=aws_config)
    aws_cognito_id = aws_cognito_client.get_id(
        IdentityPoolId=websiteconfig.aws_identity
        )['IdentityId']
    aws_credentials = aws_cognito_client.get_credentials_for_identity(
        IdentityId=aws_cognito_id
        )['Credentials']

    authenticated_session = boto3.Session(
        region_name=websiteconfig.aws_region,
        aws_access_key_id=aws_credentials['AccessKeyId'],
        aws_secret_access_key=aws_credentials['SecretKey'],
        aws_session_token=aws_credentials['SessionToken'])

    return authenticated_session


def upload_picture_file(filename: Path) -> str:
    with filename.open('rb') as f:
        return upload_picture_fileobj(f, filename.suffix)


# suffix e.g. '.jpg'
def upload_picture_fileobj(binaryfile: typing.BinaryIO, suffix: str) -> str:
    aws_s = authenticated_aws_session()
    s3 = aws_s.client('s3')

    # ref: https://github.com/mmdriley/kidstuff/blob/72664feb/websites/tinybeans/tinybeans-frontend/services/rest-backend.js#L157
    key = str(uuid.uuid4()) + suffix

    s3.upload_fileobj(binaryfile, websiteconfig.aws_bucket, key)

    return key
