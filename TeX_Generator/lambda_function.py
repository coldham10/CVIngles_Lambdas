import json
import os
import boto3
import template

SUBMISSIONS = boto3.resource("dynamodb").Table(os.environ["SUBM_TABLE"])


def s(unsanitized):
    """helper function to sanitize for LaTeX"""
    tmp = unsanitized.replace("\\", "\\textbackslash{}")
    tmp = tmp.replace("{", "\\{")
    tmp = tmp.replace("}", "\\}")
    tmp = tmp.replace("$", "\\$")
    tmp = tmp.replace("&", "\\&")
    tmp = tmp.replace("#", "\\#")
    tmp = tmp.replace("^", "")
    tmp = tmp.replace("_", "\\_")
    tmp = tmp.replace("%", "\\%")
    tmp = tmp.replace("~", "\\textasciitilde{}")
    tmp = tmp.replace("\n\n\n", "\\newline{}")
    tmp = tmp.replace("\n\n", "\\newline{}")
    tmp = tmp.replace("\n", "\\newline{}")
    return tmp


def lambda_handler(event, _):

    # High level parse of JSON & DDB table

    CID = event["ClientID"]
    # Read appropriate row from submissions table
    table_row = SUBMISSIONS.get_item(Key={"SessionID": CID})["Item"]
    if not table_row["JSONUploaded"]:
        raise RuntimeError("Error: JSON not uploaded")
    if event["Translated"] and not table_row["Translated"]:
        raise RuntimeError("Error: JSON not translated")
    # Upload and parse JSON file
    json_fname = (
        table_row["JSONFile_TRANS"] if event["Translated"] else table_row["JSONFile"]
    )
    response = boto3.client("s3").get_object(
        Bucket=os.environ["RAW_BUCKET"], Key=json_fname
    )
    data = json.loads(response["Body"].read().decode("utf-8"))

    model = data["model"]
    options = data["options"]
    use_img = data["imageStatus"] == "COMPLETE"
    styles = ["fancy", "banking", "casual"]
    style = styles[options["format"]]
    # Find object["data"] with "name": "datos" in list
    personal = next(x["data"] for x in model if x["name"] == "datos")
    personal_dict = {x["name"]: x["data"] for x in personal}

    # Begin assembling TeX file as a string

    contact_list = []
    for detail in personal_dict.keys():
        # Find all contact entries
        if detail[:7] == "contact":
            type, val = personal_dict[detail].split("__!__")
            if type == "email":
                contact_list.append(template.personal.email.format(email=s(val)))
            elif type == "phone":
                contact_list.append(
                    template.personal.phone.format(type="fixed", val=s(val))
                )
            elif type == "wa":
                # TODO: include wa icon
                contact_list.append(
                    template.personal.phone.format(type="mobile", val=s(val))
                )
            elif type == "li":
                # TODO strip full website name if given (linkedin.com/myid444 -> myid444)
                contact_list.append(
                    template.personal.social.format(type="linkedin", val=s(val))
                )
            elif type == "web":
                contact_list.append(
                    template.personal.website.format(val=s(val.split("://")[-1]))
                )
            elif type == "twitter":
                contact_list.append(
                    template.personal.social.format(type=type, val=s(val))
                )
        elif detail == "address":
            if len(personal_dict[detail]) > 0:
                # TODO: need to split address into lines
                contact_list.append(
                    template.personal.address.format(
                        line_1=s(personal_dict[detail]), line_2="", country=""
                    )
                )

    if table_row["ImgUploaded"] and use_img:
        contact_list.append(
            template.personal.picture.format(
                picture=os.path.splitext(table_row["ImgFile"])[0]
            )
        )
        if not event["Translated"]:
            # Call image resizer
            boto3.client("lambda").invoke(
                FunctionName=os.environ["RESIZE_LAMBDA"],
                InvocationType="Event",
                Payload=json.dumps({"ImageName": table_row["ImgFile"]}),
            )

    personal_str = "".join(contact_list)

    # Preamble string
    pre = template.preamble.format(
        style=style,
        color=options["color"],
        fname=s(personal_dict["fname"]),
        lname=s(personal_dict["lname"]),
        personal=personal_str,
    )

    # Body content
    sections = []

    for section in model[1:]:
        if section["name"] == "experiencia":
            experience = section["data"]
            jobs = []
            for job in experience:
                job_data = {x["name"]: x["data"] for x in job["data"]}
                achievements = []
                for desc in [x["data"] for x in job_data["achievements"]]:
                    achievements.append(template.achievement.format(desc=s(desc)))
                ach_str = template.achievements.format(list="".join(achievements))
                jobs.append(
                    template.job.format(
                        start=s(job_data["startYear"]),
                        end=s(job_data["endYear"]),
                        title=s(job_data["title"]),
                        employer=s(job_data["employer"]),
                        city=s(job_data["location"]),
                        desc=s(job_data["desc"]),
                        achievements=ach_str,
                    )
                )
            sections.append(
                template.section.format(name="Experience", content="".join(jobs))
            )

        elif section["name"] == "estudios":
            education = section["data"]
            degs = []
            for deg in education:
                deg_data = {x["name"]: x["data"] for x in deg["data"]}
                degs.append(
                    template.degree.format(
                        start=deg_data["startYear"],
                        end=deg_data["endYear"],
                        title=s(deg_data["name"]),
                        school=s(deg_data["university"]),
                        city=s(deg_data["location"]),
                        grade=s(deg_data["grade"]),
                        desc=s(deg_data["desc"]),
                    )
                )

            sections.append(
                template.section.format(name="Education", content="".join(degs))
            )
        elif section["name"] == "langs":
            languages = []
            for language in section["data"]:
                ability, lang_name = language["data"].split("__!__")
                languages.append(
                    template.language.format(
                        name=s(lang_name), ability=s(template.lang_level_dict[ability])
                    )
                )
            sections.append(
                template.section.format(name="Languages", content="".join(languages))
            )
        elif section["name"] == "interests":
            interests = []
            for interest in section["data"]:
                name, desc = interest["data"].split("__!__")
                interests.append(template.interest.format(name=s(name), desc=s(desc)))
            sections.append(
                template.section.format(name="Interests", content="".join(interests))
            )
        elif section["name"] == "thesis":
            for datum in section["data"]:
                if datum["name"] == "title":
                    name = s(datum["data"])
                elif datum["name"] == "supervisors":
                    sups = s(datum["data"])
                elif datum["name"] == "desc":
                    desc = s(datum["data"])
            sections.append(
                template.thesis.format(name=name, supervisors=sups, desc=desc)
            )
        elif section["name"] == "skills":
            skills = []
            for skill in section["data"]:
                name, desc = skill["data"].split("__!__")
                skills.append(template.custom.format(name=s(name), desc=s(desc)))
            sections.append(
                template.section.format(name="Skills", content="".join(skills))
            )
        elif section["name"][:5] == "other":
            sec_title = s(section["name"].split("__!__")[1])
            content = []
            for datum in section["data"]:
                tokens = [s(x) for x in datum["data"].split("__!__")]
                if len(tokens) == 2:
                    content.append(
                        template.custom.format(name=tokens[0], desc=tokens[1])
                    )
                elif len(tokens) == 3:
                    content.append(
                        template.custom_comment.format(
                            name=tokens[0], desc=tokens[1], comment=tokens[2]
                        )
                    )
            sections.append(
                template.section.format(name=sec_title, content="".join(content))
            )

    # Join strings together and write out as TeX file

    main = template.body.format(content="".join(sections))
    tex_str = pre + main
    tex_bytes = tex_str.encode("utf-8")

    outfile_name = CID + ("_TRANS" if event["Translated"] else "") + ".tex"

    response = boto3.client("s3").put_object(
        Bucket=os.environ["TEX_BUCKET"], Body=tex_bytes, Key=outfile_name
    )

    if event["Translated"]:
        SUBMISSIONS.update_item(
            Key={"SessionID": CID},
            UpdateExpression="SET TexProcessed_TRANS = :t, TexFile_TRANS = :f",
            ExpressionAttributeValues={":t": True, ":f": outfile_name},
        )
    else:
        SUBMISSIONS.update_item(
            Key={"SessionID": CID},
            UpdateExpression="SET TexProcessed = :t, TexFile = :f",
            ExpressionAttributeValues={":t": True, ":f": outfile_name},
        )
        # If needs translation but not yet translated: translate
        if options["service"] in ["p", "t"]:
            boto3.client("lambda").invoke(
                FunctionName=os.environ["TRANS_LAMBDA"],
                InvocationType="Event",
                Payload=json.dumps({"ClientID": CID}),
            )

    # Send message to delay queue to trigger packager
    if event["Translated"] or options["service"] not in ["p", "t"]:
        boto3.client("sqs").send_message(
            QueueUrl=os.environ["PACK_QUEUE_URL"],
            MessageBody=json.dumps(
                {
                    "ClientID": CID,
                    "Translated": event["Translated"],
                    "Image": (table_row["ImgUploaded"] and use_img),
                }
            ),
        )

    return {"statusCode": 200}
