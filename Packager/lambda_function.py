import json
import os
import tarfile
import boto3
from email.message import EmailMessage

TEX_BUCKET = boto3.resource("s3").Bucket(os.environ["TEX_BUCKET"])
SUBMISSIONS = boto3.resource("dynamodb").Table(os.environ["SUBM_TABLE"])
PACKAGE_DIR = "/tmp/package/"
TAR_NAME = "/tmp/package.tar.gz"


def lambda_handler(event, _):
    in_message = json.loads(event["Records"][0]["body"])
    CID = in_message["ClientID"]
    translated = in_message["Translated"]
    has_image = in_message["Image"]
    # Read appropriate row from submissions table
    table_row = SUBMISSIONS.get_item(Key={"SessionID": CID})["Item"]
    os.mkdir(PACKAGE_DIR)

    tarball = tarfile.open(TAR_NAME, "w:gz")
    TEX_BUCKET.download_file(table_row["TexFile"], PACKAGE_DIR + table_row["TexFile"])
    if has_image:
        # Get converted image name
        prefix, _ = os.path.splitext(table_row["ImgFile"])
        img_name = prefix + ".jpg"
        TEX_BUCKET.download_file(img_name, PACKAGE_DIR + img_name)
    if translated:
        TEX_BUCKET.download_file(
            table_row["TexFile_TRANS"], PACKAGE_DIR + table_row["TexFile_TRANS"]
        )
    tarball.add(PACKAGE_DIR, recursive=True, arcname=CID)
    tarball.close()

    # Remove temporary folder
    for fname in os.listdir(PACKAGE_DIR):
        os.remove(os.path.join(PACKAGE_DIR, fname))
    os.rmdir(PACKAGE_DIR)

    # create the email
    message = EmailMessage()
    message["To"] = os.environ["EMAIL_TO"]
    message["From"] = os.environ["EMAIL_FROM"]
    message["Subject"] = "New submission: " + CID
    with open(TAR_NAME, "rb") as f:
        message.add_attachment(
            f.read(), maintype="application", subtype="gzip", filename="content.tar.gz"
        )

    # Send the email
    ses = boto3.client("ses", os.environ["REGION"])
    ses.send_raw_email(RawMessage={"Data": message.as_string()})
    os.remove(TAR_NAME)
