import os
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask import current_app

from project.models.user_model import User
from project.api.utils import secure_file, upload_file
from project.api.authentications import authenticate

from project import db, bcrypt
from project.exceptions import APIError
from project.api.validators import email_validator, field_type_validator, required_validator

ACCESS_KEY_ID = os.getenv('aws_access_key_id')
ACCESS_SECRET_KEY = os.getenv('aws_secret_access_key')

BUCKET_NAME = "alpha-ai-profile-picture"

user_blueprint = Blueprint('user', __name__, template_folder='templates')

@user_blueprint.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'success',
        'message': 'pong V0.1!'
    })

@user_blueprint.route('/users/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': 'success',
        'message': 'pong V0.1!'
    })

@user_blueprint.route('/users/list', methods=['GET'])
def get_all_users():
    """Get all users"""
    response_object = {
        'status': 'success',
        'data': {
            'users': [user.to_json() for user in User.query.all()]
        }
    }
    return jsonify(response_object), 200

@user_blueprint.route('/users/get/<int:user_id>', methods=['GET'])
def get_single_user(user_id):
    """Get single user details"""
    response_object = {
        'status': 'fail',
        'message': 'User does not exist',
    }

    user = User.query.filter_by(id=int(user_id)).first()

    if not user:
        return jsonify(response_object), 404

    response_object['status'] = 'success'
    response_object['message'] = 'User details retrieved successfully'
    response_object['data'] = user.to_json()

    return jsonify(response_object), 200

@user_blueprint.route('/users/get', methods=['GET'])
@authenticate
def get_user_by_auth_token(resp):
    """Get single user details"""
    response_object = {
        'status': 'fail',
        'message': 'User does not exist',
    }

    user = User.query.filter_by(id=int(resp)).first()

    if not user:
        return jsonify(response_object), 404

    response_object['status'] = 'success'
    response_object['message'] = 'User details'
    response_object['data'] = user.to_json()

    return jsonify(response_object), 200

@user_blueprint.route('/users/upload', methods=['POST'])
@authenticate
def upload_picture(user_id):
    filename = None
    try:
        file = request.files['file']
        if file:
            curr_date = datetime.now()

            # create secure filename and save locally
            secured_file = secure_file(user_id, file, curr_date)
            filename = secured_file["filename"] 

            # upload file to s3 bucket
            object_url = upload_file(
                secured_file["filename"], 
                secured_file["filetype"],
                BUCKET_NAME
            )

            # delete file locally
            os.remove(filename)

            user = User.query.filter_by(id=int(user_id)).first()

            if not user:
                return jsonify({
                    'message': 'User does not exist',
                    'status': 'fail'
                }), 400

            user.profile_picture = object_url
            user.update()

            message = "File uploaded successfully!"

            return jsonify({
                "message": message,
                "status": "success",
                "data": user.to_json()
            }), 200

        else:
            return jsonify({
                "message": "Invalid payload: file not found!",
                "status": "failed"
            }), 400

    except Exception as e:
        try: os.remove(filename) 
        except: pass
        finally: return jsonify({"message": str(e), "status": "fail"}), 400


@user_blueprint.route('/users/update_info', methods=['PUT'])
@authenticate
def update_user_info(resp):
    """Update user info"""
    post_data = request.get_json()

    response_object = {
        'status': 'fail',
        'message': 'Invalid payload.',
    }

    if not post_data:
        return jsonify(response_object), 400

    try:
        user = User.query.get(resp)

        field_types = {
            "firstname": str, "lastname": str, "email": str, "password": str,
            "current_password": str, "gender": str, "profile_picture": str, "active": bool
        }

        post_data = field_type_validator(post_data, field_types)
        if post_data.get("email"): email_validator(post_data.get("email"))

        password = post_data.get('password')

        if password:
            required_fields = ["current_password"]
            required_validator(post_data, required_fields)

            current_password = post_data.get('current_password')

            if not bcrypt.check_password_hash(user.password, current_password.encode('utf-8')):
                response_object['message'] = 'Current password is incorrect.'
                return jsonify(response_object), 400

            user.password = bcrypt.generate_password_hash(password, current_app.config.get("BCRYPT_LOG_ROUNDS")).decode()
            print(user.password)

        user.firstname = post_data.get('firstname') or user.firstname
        user.lastname = post_data.get('lastname') or user.lastname
        user.email = post_data.get('email') or user.email
        user.gender = post_data.get("gender") or user.gender
        user.profile_picture = post_data.get('profile_picture') or user.profile_picture
        user.active = post_data.get('active') or user.active

        user.update()

        response_object['status'] = 'success'
        response_object['message'] = 'User info updated successfully.'
        response_object['user'] = user.to_json()

        return jsonify(response_object), 200

    except Exception as e:
        response_object['message'] = str(e)
        return jsonify(response_object), 400