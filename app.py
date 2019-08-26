import os
import uuid
import shutil
import time
from flask import Flask, request, json
from services.DownloadImageService import DownloadImageService
from services.FaceRecognitionService import FaceRecognitionService
import redis
from dotenv import load_dotenv, find_dotenv

app = Flask(__name__)

DIR_NAME_UPLOADS = 'uploads'
DIR_NAME_IMAGES = 'images'
DIR_NAME_UPLOAD_IMAGES = DIR_NAME_UPLOADS + '/' + DIR_NAME_IMAGES
DIR_NAME_SRC = 'src'
DIR_NAME_DES = 'des'

load_dotenv(find_dotenv())

redis_host = os.getenv("CNF_REDIS_HOST")
redis_port = os.getenv("CNF_REDIS_PORT")
redis_password = os.getenv("CNF_REDIS_PASS")


def _do_download(img_data, img_directory, redis_client, is_check_tag=False):
	os.makedirs(img_directory)
	download_image_src = DownloadImageService(img_directory, redis_client, is_check_tag)
	return download_image_src.do_download(img_data)


@app.route('/face-compare', methods=['POST'])
def post():
	process_id = str(uuid.uuid4())

	data = request.get_json(force=True)

	process_directory = DIR_NAME_UPLOAD_IMAGES + '/' + process_id
	if not os.path.exists(process_directory):
		os.makedirs(process_directory)

	redis_client = redis.Redis(host=redis_host, port=redis_port, password=redis_password)

	src_directory = process_directory + '/' + DIR_NAME_SRC
	src = _do_download(data['src'], src_directory, redis_client, True)

	des_directory = process_directory + '/' + DIR_NAME_DES
	des = _do_download(data['des'], des_directory, redis_client)

	time.sleep(0.125)
	face_recognition_service = FaceRecognitionService()
	data = face_recognition_service.process_face_recognition(src, des, redis_client)

	# Remove directory DES
	shutil.rmtree(des_directory)

	response = app.response_class(
		response=json.dumps(data),
		status=200,
		mimetype='application/json'
	)

	return response


if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', use_reloader=False, threaded=True)
