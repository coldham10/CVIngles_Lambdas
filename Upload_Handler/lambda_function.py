import base64
import imghdr
import json
import time

import boto3

BUCKET_NAME = os.environ["RAW_BUCKET"]
SUB_TABLE_NAME = os.environ["SUBM_TABLE"]
IP_TABLE_NAME = os.environ["IP_TABLE"]
MAX_JSON_BYTES = 20000
MAX_IMAGE_BYTES = 4e9
RESET_TIME = 60 * 60 * 24
UPLOAD_QUOTA = 20


def lambda_handler(event, context):
    ddb = boto3.client("dynamodb")
    if event["endpoint"] == "/data":
        file_content = json.dumps(event["content"])
        if len(file_content) > MAX_JSON_BYTES:
            raise UserWarning("Error: JSON object over maximum size")
        file_path = event["sessionID"] + ".json"

    elif event["endpoint"] == "/image":
        file_path = event["sessionID"] + "." + event["type"]
        file_content = base64.b64decode(base64.b64decode(event["content"]))
        # TEST: image size within limit?
        if len(file_content) > MAX_IMAGE_BYTES:
            raise UserWarning("Error: image over maximum size")
        # TEST: file matches image suffix?
        if imghdr.what("_", h=file_content) != event["type"]:
            raise TypeError(
                "Error: image with extension "
                + event["type"]
                + " has filetype "
                + str(imghdr.what("_", h=file_content))
                + event["content"]
            )
        # TEST: public IP over quota?
        response = ddb.get_item(
            TableName=IP_TABLE_NAME, Key={"IP": {"S": event["sourceIP"]}}
        )
        # Reset upload count if longer than RESET_DAYS since last upload
        if (
            "Attributes" in response
            and time.time() - response["Attributes"]["LastUpdate"]["N"] > RESET_TIME
        ):
            response = ddb.update_item(
                TableName=IP_TABLE_NAME,
                Key={"IP": {"S": event["sourceIP"]}},
                UpdateExpression="SET LastUpdate = :now, ImgUploads = :one",
                ExpressionAttributeValues={
                    ":one": {"N": "1"},
                    ":now": {"N": str(int(time.time()))},
                },
                ReturnValues="ALL_NEW",
            )
        else:
            response = ddb.update_item(
                TableName=IP_TABLE_NAME,
                Key={"IP": {"S": event["sourceIP"]}},
                UpdateExpression="ADD ImgUploads :one SET LastUpdate = :now",
                ExpressionAttributeValues={
                    ":one": {"N": "1"},
                    ":now": {"N": str(int(time.time()))},
                },
                ReturnValues="ALL_NEW",
            )
        if int(response["Attributes"]["ImgUploads"]["N"]) > UPLOAD_QUOTA:
            raise ConnectionRefusedError()

    # No errors, update DDB table for pre-upload
    try:
        ddb.update_item(
            TableName=SUB_TABLE_NAME,
            Key={"SessionID": {"S": event["sessionID"]}},
            UpdateExpression="SET UploadTS = :now, "
            + "TexProcessed = :f, "
            + "CheckedOut = :f, "
            + (
                "ImgFile = if_not_exists(ImgFile, :fn), ImgUploaded = :f"
                if event["endpoint"] == "/image"
                else "JSONFile = if_not_exists(JSONFile, :fn), JSONUploaded = :f"
            ),
            ExpressionAttributeValues={
                ":now": {"N": str(int(time.time()))},
                ":f": {"BOOL": False},
                ":fn": {"S": file_path},
            },
        )
    except Exception as e:
        raise IOError("ServerError: " + str(e) + "; SessionID: " + event["sessionID"])

    # Upload raw
    s3 = boto3.client("s3")
    try:
        s3_response = s3.put_object(
            Bucket=BUCKET_NAME, Key=file_path, Body=file_content
        )
    except Exception as e:
        raise IOError("ServerError: " + str(e))

    # Document upload success in DDB
    try:
        ddb.update_item(
            TableName=SUB_TABLE_NAME,
            Key={"SessionID": {"S": event["sessionID"]}},
            UpdateExpression="SET UploadTS = :now, "
            + (
                "ImgUploaded = :t"
                if event["endpoint"] == "/image"
                else "JSONUploaded = :t"
            ),
            ExpressionAttributeValues={
                ":now": {"N": str(int(time.time()))},
                ":t": {"BOOL": True},
            },
        )
        if event["endpoint"] == "/data" and event["content"]["imageStatus"] == "NONE":
            ddb.update_item(
                TableName=SUB_TABLE_NAME,
                Key={"SessionID": {"S": event["sessionID"]}},
                UpdateExpression="SET ImgUploaded = :f",
                ExpressionAttributeValues={":f": {"BOOL": False}},
            )
    except Exception as e:
        raise IOError("ServerError: " + str(e))

    return "update successful"
