import face_recognition
import multiprocessing
import itertools
import PIL.Image
import numpy as np
import cv2


class FaceRecognitionService(object):
	def process_face_recognition(self, src_urls, des_urls):
		# self.process_crop_bounding_box_in_process_pool(src_urls)

		known_face_encodings = self.scan_known_people(src_urls)

		tolerance = 0.6
		result_face_distance = self.process_images_in_process_pool(des_urls, known_face_encodings)
		result = -1 if (not result_face_distance or min(result_face_distance) > 1) else min(result_face_distance)

		return {
			'status': True if (tolerance > result >= 0) else False,
			'matched_faces': result,
		}

	def scan_known_people(self, file_urls):
		known_face_encodings = []

		for file_url in file_urls:
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
		except Exception as e:
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
		context = multiprocessing
		if "forkserver" in multiprocessing.get_all_start_methods():
			context = multiprocessing.get_context("forkserver")

		pool = context.Pool(processes=processes)

		function_parameters = zip(
			images_to_check,
			itertools.repeat(known_face_encodings)
		)

		result = pool.starmap(self.test_image, function_parameters)
		pool.close()

		return result

	def process_crop_bounding_box_in_process_pool(self, img_url, number_of_cpus=4):
		processes = number_of_cpus
		context = multiprocessing
		if "forkserver" in multiprocessing.get_all_start_methods():
			context = multiprocessing.get_context("forkserver")

		pool = context.Pool(processes=processes)

		function_parameters = zip(img_url)

		pool.starmap(self.crop_bounding_box, function_parameters)
		pool.close()

	def crop_bounding_box(self, img_url):
		bounding_box_image = cv2.imread(img_url)
		image = cv2.resize(bounding_box_image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		# blurred = cv2.GaussianBlur(gray, (7, 7), 0)
		edged = cv2.Canny(gray, 100, 100)
		# find contours in the edge map
		(cnts, _) = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		# loop over our contours to find hexagon
		cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:50]

		screen_cnt = None
		for c in cnts:
			# approximate the contour
			peri = cv2.arcLength(c, True)
			approx = cv2.approxPolyDP(c, 0.004 * peri, True)
			# if our approximated contour has four points, then
			# we can assume that we have found our squeare

			if len(approx) == 4:
				screen_cnt = approx
				x, y, w, h = cv2.boundingRect(c)
				# cv2.drawContours(image, [approx], -1, (0, 255, 255))
				# create the mask and remove rest of the background
				mask = np.zeros(image.shape[:2], dtype="uint8")
				cv2.drawContours(mask, [screen_cnt], -1, 255, -1)
				masked = cv2.bitwise_and(image, image, mask=mask)
				# cv2.imshow("Masked",masked  )
				# crop the masked image to to be compared to referance image
				cropped = masked[y:y + h, x:x + w]
				# scale the image so it is fixed size as referance image
				cropped = cv2.resize(cropped, (300, 300), interpolation=cv2.INTER_AREA)

				cv2.imwrite(img_url, cropped)
