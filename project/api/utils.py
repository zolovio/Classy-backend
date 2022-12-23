import os
import boto3
from werkzeug.utils import secure_filename

from project.exceptions import APIError

ACCESS_KEY_ID=os.getenv('aws_access_key_id')
ACCESS_SECRET_KEY=os.getenv('aws_secret_access_key')

REGION_NAME = "eu-west-1"

s3 = boto3.resource(
    service_name='s3',
    region_name=REGION_NAME,
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=ACCESS_SECRET_KEY
)

client = boto3.client(
    service_name='textract',
    region_name=REGION_NAME,
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key = ACCESS_SECRET_KEY
)

def upload_file(filename, filetype, bucket):
    # upload file to s3
    s3.Bucket(bucket).upload_file( 
        Filename=filename,
        Key=filename,
        ExtraArgs={
            'ACL':'public-read',        # *(if not mentioned, file will not be publically accessible)
            'ContentType': filetype     # *(if not mentioned, file will be download-able only)
        }
    )

    object_url = "https://{}.s3.{}.amazonaws.com/{}".format(bucket, REGION_NAME, filename)

    return object_url


def secure_file(user_id, file, date) -> dict:
    timestamp = str(date).split('.')[0].replace('-', '').replace(':', '')

    filename = str(file.filename).split('.')
    filename = ' '.join(filename[:-1]) + ' ' + str(user_id) + ' ' + str(timestamp) + '.' + filename[-1]
    filename = secure_filename(filename)

    filetype = file.content_type

    # verify file type
    file_ext = filetype.split('/')[-1]
    if file_ext not in ("png", "jpg", "jpeg", "tiff"):
        raise APIError("Unsupported file format: {}".format(filetype))

    # save file locally
    file.save(filename)
    filesize = os.stat(filename).st_size

    # # max allowed file size is 5 MB
    # if filesize >= (5 * 1024 * 1024): 
    #    raise APIError("Please upload file of size less than 5 MB!")

    return {
        "filename": filename,
        "filetype": filetype,
        "filesize": filesize
    }


def extract_data(document, bucket):
    response = client.analyze_expense(
        Document={
            'S3Object': {
                'Bucket': bucket,
                'Name': document
            }
        }
    )

    return response


def get_s3_buckets():
    data = {}

    for bucket in s3.buckets.all():
        data[bucket.name] = []

        for obj in s3.Bucket(bucket.name).objects.all():
            data[bucket.name].append({
                "filename": obj.key,
                "type": obj.key.split('.')[-1],
                "object_url": "https://{}.s3.{}.amazonaws.com/{}".format(bucket.name, REGION_NAME, obj.key)
            })

    return data
