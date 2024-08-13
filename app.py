from flask.json import jsonify
from constants.http_status_code import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from flask import Flask, config, redirect
import os
from flask_jwt_extended import JWTManager
from flasgger import Swagger, swag_from
from config.swagger import template, swagger_config
from flask_cors import CORS
from database import *
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv
 
from controller.users import users
from controller.sets import sets
from controller.questions import questions

# Tải các biến môi trường từ file .env
load_dotenv()

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
            SECRET_KEY=os.getenv("SECRET_KEY"),
            JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY'),
            SWAGGER={
                'title': "Bookmarks API",
                'uiversion': 3
            }
        )

ma.app=app
ma.init_app(app)
JWTManager(app)
CORS(app)

app.register_blueprint(users)
app.register_blueprint(sets)
app.register_blueprint(questions)

Swagger(app, config=swagger_config, template=template)

@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    return jsonify(error=str(e)), code


if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True,port=3000)