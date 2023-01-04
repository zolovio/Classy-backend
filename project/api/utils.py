import os
import logging
import random
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from imagekitio.client import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

from project.exceptions import APIError
from project.models import Sku, User, Coupon, Campaign, Draw

logger = logging.getLogger(__name__)

ACCESS_PRIVATE_KEY = os.getenv('IMAGEKIT_PRIVATE_KEY')
ACCESS_PUBLIC_KEY = os.getenv('IMAGEKIT_PUBLIC_KEY')
ACCESS_URL_ENDPOINT = os.getenv('IMAGEKIT_URL_ENDPOINT')

imagekit = ImageKit(
    private_key=ACCESS_PRIVATE_KEY,
    public_key=ACCESS_PUBLIC_KEY,
    url_endpoint=ACCESS_URL_ENDPOINT
)


def upload_file(file, file_name):
    response = imagekit.upload_file(
        file=file,
        file_name=file_name
    )

    return response


def secure_file(file) -> dict:
    filename = secure_filename(filename)
    filetype = file.content_type

    # verify file type
    file_ext = filetype.split('/')[-1]
    if file_ext not in ("png", "jpg", "jpeg", "tiff"):
        raise APIError("Unsupported file format: {}".format(filetype))

    # save file locally
    file.save(filename)
    filesize = os.stat(filename).st_size

    return {
        "filename": filename,
        "filetype": filetype,
        "filesize": filesize
    }


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
