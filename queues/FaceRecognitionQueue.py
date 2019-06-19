import threading

import face_recognition


class FaceRecognitionQueue(threading.Thread):
	def __init__(self, m_queue, m_results, m_lst_des_img_encoding):
		threading.Thread.__init__(self)
		self.m_queue = m_queue
		self.m_results = m_results
		self.m_lst_des_img_encoding = m_lst_des_img_encoding

	def run(self) -> None:
		while True:
			msg_queue = self.m_queue.get()
			from services.FaceRecognitionService import FaceRecognitionService
			face_recognition_service = FaceRecognitionService()

			des_url = msg_queue.des_url

			des_face_encodings = None

			if des_url in self.m_lst_des_img_encoding.keys():
				print('Url {} encoded'.format(des_url))
				des_face_encodings = self.m_lst_des_img_encoding[des_url]
			else:
				des_image = face_recognition.load_image_file(des_url)
				try:
					des_face_encodings = face_recognition.face_encodings(des_image)[0]
					self.m_lst_des_img_encoding[des_url] = des_face_encodings
					print('#1 Put {} des face encodings to list'.format(des_url))
					print(self.m_lst_des_img_encoding.keys())
				except IndexError:
					try:
						des_face_locations = face_recognition.face_locations(des_image, model="cnn")
						des_face_encodings = face_recognition.face_encodings(des_image, des_face_locations)[0]
						self.m_lst_des_img_encoding[des_url] = des_face_encodings
						print('#2 Put {} des face encodings to list'.format(des_url))
						print(self.m_lst_des_img_encoding.keys())
					except (IndexError, RuntimeError) as err:
						print(str(err))

			if des_face_encodings is not None:
				face_distance = face_recognition_service.compare_face(
					msg_queue.src_img,
					des_face_encodings
				)
			else:
				face_distance = 999

			self.m_results.append(face_distance)
			self.m_queue.task_done()
