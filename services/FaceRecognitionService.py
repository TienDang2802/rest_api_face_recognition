import os
import pickle
import face_recognition
import multiprocessing
import itertools
import PIL.Image
import numpy as np
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
cache_ttl = os.getenv("CACHE_TTL")


class FaceRecognitionService(object):
	def process_face_recognition(self, src_urls, des_urls, redis_client):
		known_face_encodings = self.__scan_known_people(src_urls, redis_client)

		tolerance = 0.6
		result_face_distance = self.process_images_in_process_pool(des_urls, known_face_encodings)
		result = -1 if (not result_face_distance or min(result_face_distance) > 1) else min(result_face_distance)

		return {
			'status': True if (tolerance > result >= 0) else False,
			'matched_faces': result,
		}

	def __scan_known_people(self, file_urls, redis_client):
		known_face_encodings = []

		for file_url in file_urls:
			if isinstance(file_url, bytes):
				file_url = file_url.decode("utf-8")
			img_name = os.path.basename(file_url)
			if redis_client.exists(img_name):
				encodings_cache = pickle.loads(redis_client.get(img_name))
				known_face_encodings.append(encodings_cache)
			else:
				file_url = "./{}".format(file_url)
				print('>>>>> File URL', file_url)
				img = face_recognition.load_image_file(file_url)
				encodings = face_recognition.face_encodings(img)

				if len(encodings) == 0:
					try:
						face_locations = face_recognition.face_locations(img, model="cnn")
						encodings = face_recognition.face_encodings(img, face_locations)
					except (IndexError, MemoryError, RuntimeError) as err:
						print("===> ERROR:", err)
						print("===> No faces found in {}".format(file_url))
						continue
					if len(encodings) == 0:
						print("WARNING: No faces found in {}. Ignoring file.".format(file_url))
					else:
						known_face_encodings.append(encodings[0])
				else:
					known_face_encodings.append(encodings[0])

				cache_value_json_string = pickle.dumps(encodings[0])
				redis_client.set(img_name, cache_value_json_string, ex=cache_ttl)

		return known_face_encodings

	def test_image(self, image_to_check, known_face_encodings):
		if not known_face_encodings:
			return 999

		unknown_image = face_recognition.load_image_file(image_to_check)

		# Scale down image if it's giant so things run a little faster
		if max(unknown_image.shape) > 1600:
			pil_img = PIL.Image.fromarray(unknown_image)
			pil_img.thumbnail((1600, 1600), PIL.Image.LANCZOS)
			unknown_image = np.array(pil_img)

		try:
			unknown_encodings = face_recognition.face_encodings(unknown_image)
		except (IndexError, MemoryError, RuntimeError, Exception) as e:
			print('>>> ERROR: ', e)
			return 999

		if not unknown_encodings:
			return 999

		for unknown_encoding in unknown_encodings:
			distance = face_recognition.face_distance(known_face_encodings, unknown_encoding)
			return min(distance)

	def process_images_in_process_pool(self, images_to_check, known_face_encodings, number_of_cpus=4):
		print('Process image: ', images_to_check)
		if number_of_cpus == -1:
			processes = None
		else:
			processes = number_of_cpus

		# macOS will crash due to a bug in libdispatch if you don't use 'forkserver'
		context = multiprocessing.get_context('spawn')
		if "forkserver" in multiprocessing.get_all_start_methods():
			context = multiprocessing.get_context("forkserver")

		pool = context.Pool(processes=processes, maxtasksperchild=100)

		function_parameters = zip(
			images_to_check,
			itertools.repeat(known_face_encodings)
		)

		result = pool.starmap(self.test_image, function_parameters, chunksize=50)
		pool.close()
		pool.terminate()
		pool.join()

		return result
