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
    msg_b = response["Body"].read()
    msg = email.message_from_bytes(msg_b)
    return msg


def create_message(reply, original):
    if "Reply-To" in reply.keys():
        del reply["Reply-To"]
    reply["Reply-To"] = original["To"]
    subj = reply["Subject"].split(delimiter)[0]
    del reply["Subject"]
    reply["Subject"] = subj
    del reply["To"]
    if "Reply-To" in original.keys():
        reply["To"] = original["Reply-To"]
    else:
        reply["To"] = original["From"]
    del reply["From"]
    reply["From"] = original["To"]
    msg_str = reply.as_string()
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
    reply_id = event["Records"][0]["ses"]["mail"]["messageId"]
    print(f"Received message ID {reply_id}")
    reply_msg = get_message_from_s3(reply_id)
    # Get the original message being replied to
    print(reply_msg["Subject"])
    original_id = reply_msg["Subject"].split(delimiter)[1]
    original_msg = get_message_from_s3(original_id)
    message = create_message(reply_msg, original_msg)
    result = send_email(message)
    print(result)
