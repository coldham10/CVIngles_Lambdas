import json
import boto3

TRANSLATOR = boto3.client("translate")
SUBMISSIONS = boto3.resource("dynamodb").Table(os.environ["SUBM_TABLE"])
NO_TRANSLATE = [
    "datos",
    "startYear",
    "endYear",
    "employer",
    "location",
    "grade",
    "university",
    "supervisors",
]
# Language codes
SLC = "es"
TLC = "en"


def recursive_translate(section):
    if section["name"] in NO_TRANSLATE:
        return
    if section["name"][:5] == "other":
        # custom section name, e.g. other0__!__Voluntario
        tokens = section["name"].split("__!__")
        if len(tokens[1]) > 0:
            response = TRANSLATOR.translate_text(
                Text=tokens[1], SourceLanguageCode=SLC, TargetLanguageCode=TLC
            )
            section["name"] = tokens[0] + "__!__" + response["TranslatedText"]
    if type(section["data"]) == list:
        # Not a final/leaf data string, recurse down
        for subsection in section["data"]:
            recursive_translate(subsection)
    else:
        # String data, could be composite with "__!__" separators
        tokens = section["data"].split("__!__")
        trans_tokens = []
        for token in tokens:
            if len(token) > 0:
                response = TRANSLATOR.translate_text(
                    Text=token, SourceLanguageCode=SLC, TargetLanguageCode=TLC
                )
                trans_tokens.append(response["TranslatedText"])
            else:
                trans_tokens.append("")
        section["data"] = "__!__".join(trans_tokens)


def lambda_handler(event, _):
    CID = event["ClientID"]
    CID_TRANS = CID + "_TRANS"
    # Read appropriate row from submissions table
    table_row = SUBMISSIONS.get_item(Key={"SessionID": CID})["Item"]
    if not table_row["JSONUploaded"]:
        raise RuntimeError("Error: JSON not uploaded")
    # Upload and parse JSON file
    response = boto3.client("s3").get_object(
        Bucket=os.environ["RAW_BUCKET"], Key=table_row["JSONFile"]
    )
    data = json.loads(response["Body"].read().decode("utf-8"))
    for section in data["model"]:
        recursive_translate(section)
    translated_json_b = json.dumps(data).encode("utf-8")
    translated_json_name = CID_TRANS + ".json"
    boto3.client("s3").put_object(
        Bucket=os.environ["RAW_BUCKET"],
        Body=translated_json_b,
        Key=translated_json_name,
    )
    SUBMISSIONS.update_item(
        Key={"SessionID": CID},
        UpdateExpression="SET Translated = :t, JSONFile_TRANS = :f",
        ExpressionAttributeValues={":t": True, ":f": translated_json_name},
    )
    boto3.client("lambda").invoke(
        FunctionName=os.environ["GEN_LAMBDA"],
        InvocationType="Event",
        Payload=json.dumps({"ClientID": CID, "Translated": True}),
    )

    return {"statusCode": 200, "body": json.dumps("Success")}
