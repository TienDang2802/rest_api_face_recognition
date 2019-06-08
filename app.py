import glob
import io
import json
import os
import shutil
import threading
import uuid
import numpy as np

import face_recognition
import requests
from flask import Flask, request
from flask_restful import Resource, Api
from PIL import Image

app = Flask(__name__)
api = Api(app)


class FaceCompareAPI(Resource):
	def post(self):
		process_id = uuid.uuid4()

		data = request.get_json(force=True)

		total_img_src = len(data['src'])
		print('Total img src: ' + str(total_img_src))
		total_img_des = len(data['des'])
		print('Total img des: ' + str(total_img_des))

		process_directory = 'images/' + str(process_id)
		if not os.path.exists(process_directory):
			os.makedirs(process_directory)

		src_directory = process_directory + '/src'
		os.makedirs(src_directory)

		des_directory = process_directory + '/des'
		os.makedirs(des_directory)

		# src_threads = []
		#
		# for i in range(6):
		# 	t = threading.Thread(target=fetch_url_src, args=(data['src'], src_directory))
		# 	src_threads.append(t)
		# 	t.start()
		#
		# for x in src_threads:
		# 	x.join()

		fetch_url_src(data['src'], src_directory)

		# des_threads = []
		# for i in range(6):
		# 	t = threading.Thread(target=fetch_url_des, args=(data['des'], des_directory))
		# 	des_threads.append(t)
		# 	t.start()
		#
		# for x in des_threads:
		# 	x.join()
		fetch_url_des(data['des'], des_directory)

		src_files = glob.glob("{}/*.jpg".format(src_directory))
		src_files.extend(glob.glob("{}/*.jpeg".format(src_directory)))
		src_files.extend(glob.glob("{}/*.png)".format(src_directory)))
		src_files.extend(glob.glob("{}/*.gif)".format(src_directory)))

		src_file_url = []
		for src_file in src_files:
			src_file_url.append(src_file)

		des_files = glob.glob("{}/*.jpg".format(des_directory))
		des_files.extend(glob.glob("{}/*.jpeg".format(des_directory)))
		des_files.extend(glob.glob("{}/*.png".format(des_directory)))
		des_files.extend(glob.glob("{}/*.gif".format(des_directory)))
		des_file_url = []
		for des_file in des_files:
			des_file_url.append(des_file)

		data = process_face_recognition(src_file_url, des_file_url)

		shutil.rmtree(process_directory)

		return data, 200


api.add_resource(FaceCompareAPI, '/face-compare', endpoint='face-compare')


def download_image(out_dir, img_url):
	r = requests.get(img_url, timeout=4.0)
	if r.status_code != requests.codes.ok:
		assert False, 'Status code error: {}.'.format(r.status_code)

	with Image.open(io.BytesIO(r.content)) as im:
		filename = str(uuid.uuid4()) + '.' + im.format
		image_file_path = os.path.join(out_dir, filename.lower())
		im.save(image_file_path)

	print('Image downloaded from url: {} and saved to: {}'.format(img_url, image_file_path))


def fetch_url_src(uris, path):
	for uri in uris:
		download_image(path, uri)
		if not os.path.exists(path):
			r = requests.get(uri, stream=True)
			if r.status_code == 200:
				with open(path, 'wb') as f:
					for chunk in r:
						f.write(chunk)


def fetch_url_des(uris, path):
	for uri in uris:
		download_image(path, uri)
		if not os.path.exists(path):
			r = requests.get(uri, stream=True)
			if r.status_code == 200:
				with open(path, 'wb') as f:
					for chunk in r:
						f.write(chunk)


def process_face_recognition(src_urls, des_urls):
	result = {
		'status': False,
		'matched_faces': None
	}
	matched_faces = []
	for src_url in src_urls:
		for des_url in des_urls:
			known_image = face_recognition.load_image_file(src_url)
			unknown_image = face_recognition.load_image_file(des_url)

			known_image_encoding = face_recognition.face_encodings(known_image)
			if len(known_image_encoding) == 0:
				print('Calculate src')
				face_locations = face_recognition.face_locations(known_image, number_of_times_to_upsample=0, model="cnn")
				known_image_encoding = face_recognition.face_encodings(known_image, face_locations)

			known_image_encoding = known_image_encoding[0]

			unknown_face_encodings = face_recognition.face_encodings(unknown_image)
			if len(unknown_face_encodings) == 0:
				print('Calculate unknown')
				unknown_face_locations = face_recognition.face_locations(unknown_image, number_of_times_to_upsample=0,
				                                                         model="cnn")
				unknown_face_encodings = face_recognition.face_encodings(unknown_image, unknown_face_locations)

			unknown_face_encodings = unknown_face_encodings[0]

			results_compare_faces = face_recognition.compare_faces([known_image_encoding], unknown_face_encodings)[0]
			results_face_distance = face_recognition.face_distance([known_image_encoding], unknown_face_encodings)[0]
			matched_faces.append(results_face_distance)

			is_match_face = json.dumps(results_compare_faces.tolist())
			if is_match_face == 'true':
				matched_faces.sort()

				result['status'] = True
				result['matched_faces'] = matched_faces

				return result

	matched_faces.sort()
	result['matched_faces'] = matched_faces

	return result


if __name__ == "__main__":
	app.run(host='0.0.0.0')
