from queue import Queue

import face_recognition

from QueueMessages.FaceRecognitionQueueMessage import FaceRecognitionQueueMessage
from queues.FaceRecognitionQueue import FaceRecognitionQueue


class FaceRecognitionService(object):
	NUM_FETCH_THREADS = 30

	def process_face_recognition(self, src_urls, des_urls):
		results_face_distance = []
		lst_des_img_encoding = {}

		face_recognition_queue = Queue()

		for src_url in src_urls:
			src_image = face_recognition.load_image_file(src_url)
			try:
				src_image_encoding = face_recognition.face_encodings(src_image)[0]
			except IndexError:
				continue

			for des_url in des_urls:
				queue_message = FaceRecognitionQueueMessage(src_image_encoding, des_url)
				face_recognition_queue.put(queue_message)

		for i in range(self.NUM_FETCH_THREADS):
			worker = FaceRecognitionQueue(face_recognition_queue, results_face_distance, lst_des_img_encoding)
			worker.setDaemon(True)
			worker.start()

		face_recognition_queue.join()

		matched_faces = min(results_face_distance)

		return {
			'status': True if matched_faces < 0.6 else False,
			'matched_faces': matched_faces,
		}

	def compare_face(self, src_img_encoding, des_face_encodings):
		return face_recognition.face_distance([src_img_encoding], des_face_encodings)[0]
