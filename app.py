import glob
import os
import shutil
import uuid
from flask import Flask, request, json
from werkzeug.utils import secure_filename

from services.DownloadImageService import DownloadImageService
from services.FaceRecognitionService import FaceRecognitionService

app = Flask(__name__)

IMG_DIR_NAME = 'images'
SRC_DIR_NAME = 'src'
DES_DIR_NAME = 'des'


@app.route('/face-compare', methods=['POST'])
def post():
	process_id = str(uuid.uuid4())

	data = request.get_json(force=True)

	total_img_src = len(data['src'])
	print('Total img src: ' + str(total_img_src))
	total_img_des = len(data['des'])
	print('Total img des: ' + str(total_img_des))

	process_directory = IMG_DIR_NAME + '/' + process_id
	if not os.path.exists(process_directory):
		os.makedirs(process_directory)

	src_directory = process_directory + '/' + SRC_DIR_NAME
	os.makedirs(src_directory)

	des_directory = process_directory + '/' + DES_DIR_NAME
	os.makedirs(des_directory)

	print('Process download img SRC')
	download_image_src = DownloadImageService()
	download_image_src.do_download(data['src'], src_directory)

	print('Process download img DES')
	download_image_des = DownloadImageService()
	download_image_des.do_download(data['des'], des_directory)

	src_file_url = []
	src_files = glob.glob("{}/*.*".format(src_directory))
	for src_file in src_files:
		src_file_url.append(src_file)

	des_file_url = []
	des_files = glob.glob("{}/*.*".format(des_directory))
	for des_file in des_files:
		des_file_url.append(des_file)

	face_recognition_service = FaceRecognitionService()
	data = face_recognition_service.process_face_recognition(src_file_url, des_file_url)

	shutil.rmtree(process_directory)

	response = app.response_class(
		response=json.dumps(data),
		status=200,
		mimetype='application/json'
	)
	return response


@app.route('/face-compare-upload', methods=['GET', 'POST'])
def upload_file():
	process_id = uuid.uuid4()
	file = request.files['file']

	result = {
		'message': 'Please upload file'
	}
	if file:
		process_directory = IMG_DIR_NAME + '/' + str(process_id)
		if not os.path.exists(process_directory):
			os.makedirs(process_directory)

		filename = secure_filename(file.filename)
		src_directory = process_directory + '/' + SRC_DIR_NAME
		os.makedirs(src_directory)
		src_file_path = os.path.join(src_directory, filename)
		file.save(src_file_path)
		print('Finish upload img SRC: ' + src_file_path)

		request_des_urls = request.values['des'].split(',')
		total_img_des = len(request_des_urls)

		des_directory = process_directory + '/' + DES_DIR_NAME
		os.makedirs(des_directory)

		print('Total img des: ' + str(total_img_des))
		print('Process download img DES')

		download_image_des = DownloadImageService()
		download_image_des.do_download(request_des_urls, des_directory)

		src_file_url = [src_file_path]

		des_file_url = []
		des_files = glob.glob("{}/*.*".format(des_directory))
		for des_file in des_files:
			des_file_url.append(des_file)

		face_recognition_service = FaceRecognitionService()
		result = face_recognition_service.process_face_recognition(src_file_url, des_file_url)

		shutil.rmtree(process_directory)

	response = app.response_class(
		response=json.dumps(result),
		status=200,
		mimetype='application/json'
	)

	return response


if __name__ == "__main__":
	app.run(host='0.0.0.0', debug=False, threaded=True, use_reloader=False)
