import os
import logging
import random
from datetime import datetime, timedelta
import boto3
from werkzeug.utils import secure_filename

from project.exceptions import APIError
from project.models import Sku, User, Coupon, Campaign, Draw

logger = logging.getLogger(__name__)

# ACCESS_KEY_ID=os.getenv('aws_access_key_id')
# ACCESS_SECRET_KEY=os.getenv('aws_secret_access_key')

# REGION_NAME = "eu-west-1"

# s3 = boto3.resource(
#     service_name='s3',
#     'region_name=REGION_NAME,
#     aws_access_key_id=ACCESS_KEY_ID,
#     aws_secret_access_key=ACCESS_SECRET_KEY
# )

# client = boto3.client(
#     service_name='textract',
#     'region_name=REGION_NAME,
#     aws_access_key_id=ACCESS_KEY_ID,
#     aws_secret_access_key = ACCESS_SECRET_KEY
# )

# def upload_file(filename, filetype, bucket):
#     # upload file to s3
#     s3.Bucket(bucket).upload_file(
#         Filename=filename,
#         Key=filename,
#         ExtraArgs={
#             'ACL':'public-read',        # *(if not mentioned, file will not be publically accessible)
#             'ContentType': filetype     # *(if not mentioned, file will be download-able only)
#         }
#     )

#     object_url = "https://{}.s3.{}.amazonaws.com/{}".format(bucket, REGION_NAME, filename)

#     return object_url


def secure_file(user_id, file, date) -> dict:
    timestamp = str(date).split('.')[0].replace('-', '').replace(':', '')

    filename = str(file.filename).split('.')
    filename = ' '.join(filename[:-1]) + ' ' + str(user_id) + \
        ' ' + str(timestamp) + '.' + filename[-1]
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


# def extract_data(document, bucket):
#     response = client.analyze_expense(
#         Document={
#             'S3Object': {
#                 'Bucket': bucket,
#                 'Name': document
#             }
#         }
#     )

#     return response


# def get_s3_buckets():
#     data = {}

#     for bucket in s3.buckets.all():
#         data[bucket.name] = []

#         for obj in s3.Bucket(bucket.name).objects.all():
#             data[bucket.name].append({
#                 "filename": obj.key,
#                 "type": obj.key.split('.')[-1],
#                 "object_url": "https://{}.s3.{}.amazonaws.com/{}".format(bucket.name, REGION_NAME, obj.key)
#             })

#     return data


def refresh_campaigns():
    # get all active campaigns
    campaigns = Campaign.query.filter(Campaign.start_date != None).all()

    for campaign in campaigns:
        # get sku for campaign
        sku = Sku.query.get(campaign.sku_id)
        # get draw for campaign
        draw = Draw.query.filter_by(campaign_id=campaign.id).first()

        if sku.quantity != sku.number_delivered and not campaign.is_active:
            # set campaign as inactive
            campaign.end_date = None
            campaign.is_active = True
            campaign.update()

            # set draw as inactive
            draw.start_date = None
            draw.end_date = None
            draw.update()

        elif sku.quantity == sku.number_delivered and campaign.is_active:
            # set campaign as inactive
            campaign.end_date = datetime.now()
            campaign.is_active = False
            campaign.update()

            # set draw as active
            draw.start_date = datetime.now()
            draw.end_date = draw.start_date + timedelta(days=7)
            draw.update()


def lucky_draw():
    draws = Draw.query.filter(
        Draw.end_date >= datetime.now(), Draw.winner_id == None).all()

    logger.info("Processing {} draws".format(len(draws)))

    for draw in draws:
        campaign = Campaign.query.get(draw.campaign_id)

        # get all users who have entered the campaign
        users = User.query.join(
            Coupon, User.id == Coupon.user_id).filter(
            Coupon.campaign_id == campaign.id).all()

        # get random user
        winner = random.choice(users)

        # set winner
        draw.winner_id = winner.id
        draw.update()

        return winner
