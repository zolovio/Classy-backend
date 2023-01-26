import os
import base64
import random
import logging
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from imagekitio.client import ImageKit

# from project import scheduler
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


def upload_file(file_object):
    try:
        secured_file = secure_file(file_object)
        filename = secured_file["filename"]

        # get current path
        current_path = os.path.dirname(os.path.abspath(__name__))
        file_path = os.path.join(current_path, filename)
        logger.info("File path: {}".format(file_path))

        with open(file_path, mode="rb") as img:
            imgstr = base64.b64encode(img.read())

        response = imagekit.upload_file(
            file=imgstr,
            file_name=filename
        )

        # delete file
        os.remove(filename)
    except Exception as e:
        logger.error("Error: {}".format(e))
        raise APIError("Error uploading file: {}".format(e))

    return response


def secure_file(file) -> dict:
    filename = secure_filename(file.filename)
    filetype = file.content_type

    # # verify file type
    # file_ext = filetype.split('/')[-1]
    # if file_ext not in ("png", "jpg", "jpeg", "tiff"):
    #     raise APIError("Unsupported file format: {}".format(filetype))

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

        if sku.quantity != sku.number_sold and not campaign.is_active:
            # set campaign as inactive
            campaign.end_date = None
            campaign.is_active = True
            campaign.update()

            # set draw as inactive
            draw.start_date = None
            draw.end_date = None
            draw.update()

        elif campaign.is_active:
            if sku.quantity == sku.number_delivered or sku.quantity == sku.number_sold:
                # set campaign as inactive
                campaign.end_date = datetime.now()
                campaign.is_active = False
                campaign.update()

            if sku.quantity == sku.number_delivered:
                # set draw as active
                draw.start_date = datetime.now()
                draw.end_date = draw.start_date + timedelta(days=7)
                draw.update()

            elif sku.quantity == sku.number_sold:
                # set draw as inactive
                draw.start_date = None
                draw.end_date = None
                draw.update()

    # with open('cronjob.log', 'a') as f:
    #     f.write(
    #         f"Cronjob:refresh_campaigns[{datetime.now()}]:campaigns refreshed!\n")


def lucky_draw():
    draws = Draw.query.filter(
        Draw.end_date >= datetime.now(), Draw.winner_id == None).all()

    # with open('cronjob.log', 'a') as f:
    #     f.write(
    #         f"Cronjob:refresh_campaigns[{datetime.now()}]:Processing {len(draws)} draws!\n")

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

    # with open('cronjob.log', 'a') as f:
    #     f.write(
    #         f"Cronjob:refresh_campaigns[{datetime.now()}]:draws updated!\n")

# @scheduler.task("interval", id="lucky_draw_task", seconds=0)
# def lucky_draw_task():
#     print("running task")
#     refresh_campaigns()
#     lucky_draw()
