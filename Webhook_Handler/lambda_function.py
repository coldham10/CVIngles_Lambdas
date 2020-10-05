import os
import stripe
import json
import base64
import boto3
import botocore

WEBHOOK_SECRET = os.environ["WH_SECRET"]
STRIPE_API_SK = os.environ["API_KEY"]


def lambda_handler(event, context):
    try:
        stripe.api_key = STRIPE_API_SK
        payload = event["raw-body"].encode("utf-8")
        sig_header = event["signature"]
        stripe_event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )

        ddb = boto3.resource("dynamodb")
        PAYMENTS = ddb.Table(os.environ["PAY_TABLE"])
        SUBMISSIONS = ddb.Table(os.environ["SUBM_TABLE"])
        if stripe_event["type"] == "checkout.session.completed":
            CID = stripe_event["data"]["object"]["client_reference_id"]
            PAYMENTS.update_item(
                Key={
                    "PaymentIntentID": stripe_event["data"]["object"]["payment_intent"]
                },
                UpdateExpression="SET ClientRefID = :crid",
                ExpressionAttributeValues={":crid": CID},
            )
            SUBMISSIONS.update_item(
                Key={"SessionID": CID},
                UpdateExpression="SET CheckedOut = :t",
                ExpressionAttributeValues={":t": True},
            )
            boto3.client("lambda").invoke(
                FunctionName=os.environ["TEX_LAMBDA"],
                InvocationType="Event",
                Payload=json.dumps({"ClientID": CID, "Translated": False}),
            )
        elif stripe_event["type"] == "payment_intent.created":
            PAYMENTS.update_item(
                Key={"PaymentIntentID": stripe_event["data"]["object"]["id"]},
                UpdateExpression="SET Amount = :amt, Currency = :cur",
                ExpressionAttributeValues={
                    ":amt": stripe_event["data"]["object"]["amount"],
                    ":cur": stripe_event["data"]["object"]["currency"],
                },
            )
        elif stripe_event["type"] == "payment_intent.succeeded":
            PAYMENTS.update_item(
                Key={"PaymentIntentID": stripe_event["data"]["object"]["id"]},
                UpdateExpression="SET Success = :t",
                ExpressionAttributeValues={":t": True},
            )

    except stripe.error.SignatureVerificationError:
        raise ValueError("Error: invalid signature")
    except botocore.exceptions.ClientError:
        raise IOError("Server Error: client error")

    else:
        return "success"
