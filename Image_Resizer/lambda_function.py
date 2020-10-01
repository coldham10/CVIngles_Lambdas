import os
import json
import boto3
from PIL import Image

RAWBUCKET = boto3.resource("s3").Bucket(os.environ["RAW_BUCKET"])
TEXBUCKET = boto3.resource("s3").Bucket(os.environ["TEX_BUCKET"])
INPATH = "/tmp/IN/"
OUTPATH = "/tmp/OUT/"
OUTPUT_HEIGHT = 250


def lambda_handler(event, context):
    os.mkdir(INPATH)
    os.mkdir(OUTPATH)
    in_name = event["ImageName"]
    print(INPATH + in_name)
    RAWBUCKET.download_file(in_name, INPATH + in_name)

    prefix, _ = os.path.splitext(in_name)
    out_name = prefix + ".jpg"

    in_image = Image.open(INPATH + in_name)
    in_size = in_image.size
    scale_factor = OUTPUT_HEIGHT / in_size[1]
    out_size = [int(d * scale_factor) for d in in_size] if scale_factor < 1 else in_size
    out_image = in_image.resize(out_size)
    out_image.save(OUTPATH + out_name, "JPEG")
    TEXBUCKET.upload_file(Filename=OUTPATH + out_name, Key=out_name)
    os.remove(INPATH + in_name)
    os.rmdir(INPATH)
    os.remove(OUTPATH + out_name)
    os.rmdir(OUTPATH)

    return out_name
