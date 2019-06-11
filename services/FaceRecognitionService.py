import json

import face_recognition


class FaceRecognitionService(object):
	def process_face_recognition(self, src_urls, des_urls):
		result = {
			'status': False,
			'matched_faces': None
		}

		for src_url in src_urls:
			matched_faces = []
			for des_url in des_urls:
				known_image = face_recognition.load_image_file(src_url)
				unknown_image = face_recognition.load_image_file(des_url)

				try:
					known_image_encoding = face_recognition.face_encodings(known_image)[0]
				except IndexError:
					try:
						face_locations = face_recognition.face_locations(known_image, number_of_times_to_upsample=0,
						                                                 model="cnn")
						known_image_encoding = face_recognition.face_encodings(known_image, face_locations)
						if len(known_image_encoding) == 0:
							continue
						known_image_encoding = known_image_encoding[0]
					except RuntimeError as err:
						print('Error face_locations of SRC: ' + src_url)
						print(str(err))

						return {
							'status': False,
							'matched_faces': -1
						}

				try:
					unknown_face_encodings = face_recognition.face_encodings(unknown_image)[0]
				except IndexError:
					try:
						unknown_face_locations = face_recognition.face_locations(unknown_image,
						                                                         number_of_times_to_upsample=0,
						                                                         model="cnn")
						unknown_face_encodings = face_recognition.face_encodings(unknown_image, unknown_face_locations)
						if len(unknown_face_encodings) == 0:
							continue
						unknown_face_encodings = unknown_face_encodings[0]
					except RuntimeError as err:
						print('=======================================')
						print('Error face_locations of DES: ' + des_url)
						print(str(err))

						return {
							'status': False,
							'matched_faces': -1
						}

				results_compare_faces = face_recognition.compare_faces([known_image_encoding], unknown_face_encodings)[
					0]
				results_face_distance = face_recognition.face_distance([known_image_encoding], unknown_face_encodings)[
					0]
				matched_faces.append(results_face_distance)

				is_match_face = json.dumps(results_compare_faces.tolist())
				if is_match_face == 'true':
					matched_faces.sort()

					result['status'] = True
					result['matched_faces'] = results_face_distance

					return result

		if not matched_faces:
			matched_faces_value = -1
		else:
			matched_faces.sort()
			matched_faces_value = min(matched_faces)

		result['matched_faces'] = matched_faces_value

		return result
