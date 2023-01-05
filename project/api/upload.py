import os
import base64
import logging

from flask import Blueprint, jsonify, request
from project.api.utils import secure_file, upload_file
from project.api.authentications import authenticate


upload_blueprint = Blueprint('upload', __name__, template_folder='templates')
logger = logging.getLogger(__name__)


@upload_blueprint.route('/upload/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@upload_blueprint.route('/upload/image', methods=['POST'])
@authenticate
def upload_image(user_id):
    filename = None
    try:
        # get file from request
        file = request.files['file']
        if file:
            # secure file
            secured_file = secure_file(file)
            filename = secured_file["filename"]

            # get current path
            current_path = os.path.dirname(os.path.abspath(__name__))
            file_path = os.path.join(current_path, filename)
            logger.info("File path: {}".format(file_path))

            # read binary file and encode it to base64
            with open(file_path, mode="rb") as img:
                imgstr = base64.b64encode(img.read())

            # upload file
            response = upload_file(imgstr, filename)
            object_url = response.url

            logger.info("File uploaded successfully: {}".format(object_url))

            # delete file locally
            os.remove(filename)

            # return response
            return jsonify({
                'status': True,
                'message': 'File uploaded successfully',
                'image_url': object_url
            }), 200

        else:
            return jsonify({
                'status': False,
                'message': "Invalid payload: file not found!"
            }), 400

    except Exception as e:
        try:
            logger.error("Error uploading file: {}".format(e))
            os.remove(filename)
        except:
            pass
        finally:
            return jsonify({"message": str(e), "status": False}), 400
