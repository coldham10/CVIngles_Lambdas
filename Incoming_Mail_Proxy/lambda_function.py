import os
import boto3
from botocore.exceptions import ClientError

import email
from email.message import EmailMessage

region = os.environ["Region"]
delimiter = "|$+$|"


def get_message_from_s3(message_id):
    client = boto3.client("s3")
    response = client.get_object(Bucket=os.environ["MailS3Bucket"], Key=message_id)
    # Read the content of the message.
    inbound_bytes = response["Body"].read()
    in_msg = email.message_from_bytes(inbound_bytes)
    return in_msg


def create_message(msg, message_id):
    if "Reply-To" in msg.keys():
        del msg["Reply-To"]
    msg["Reply-To"] = os.environ["PROXY_ADDR"]
    subj = msg["Subject"]
    del msg["Subject"]
    msg["Subject"] = subj + delimiter + message_id
    del msg["To"]
    msg["To"] = os.environ["OwnerEmail"]
    msg_str = msg.as_string()
    return msg_str


def send_email(message):
    client_ses = boto3.client("ses", region)
    # Send the email.
    try:
        # Provide the contents of the email.
        response = client_ses.send_raw_email(RawMessage={"Data": message})

    except ClientError as e:
        output = e.response["Error"]["Message"]
    else:
        output = "Email sent! Message ID: " + response["MessageId"]

    return output


def lambda_handler(event, context):
    message_id = event["Records"][0]["ses"]["mail"]["messageId"]
    print(f"Received message ID {message_id}")
    file = get_message_from_s3(message_id)
    message = create_message(file, message_id)
    result = send_email(message)
    print(result)
