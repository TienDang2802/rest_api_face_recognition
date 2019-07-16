import os
import io
import threading
from queue import Queue
import os
import socket
import threading
import uuid

import requests
import urllib3
from PIL import Image
from QueueMessages.ImageQueueMessage import ImageQueueMessage
from queues.DownloadQueue import DownloadQueue


class DownloadImageService(object):
	NUM_FETCH_THREADS = 20

	def __init__(self, num_fetch_threads=None):
		if num_fetch_threads:
			self.num_fetch_threads = num_fetch_threads
		else:
			self.num_fetch_threads = self.NUM_FETCH_THREADS

		self.download_queue = Queue()
		self.threads = []

	def do_download(self, uris, img_directory: str):
		if not os.path.exists(img_directory):
			os.makedirs(img_directory)

		self.__fetch_url_src(uris, img_directory)

		for i in range(self.num_fetch_threads):
			t = threading.Thread(target=self.worker)
			t.setDaemon(True)
			t.start()
			self.threads.append(t)

		# block until all tasks are done
		self.download_queue.join()

		# stop workers
		for i in range(self.num_fetch_threads):
			self.download_queue.put(None)
		for t in self.threads:
			t.join()

		print('Process download done')

	def __fetch_url_src(self, uris, path_dir):
		for uri in uris:
			queue_message = ImageQueueMessage(uri, path_dir)
			self.download_queue.put(queue_message)

	def worker(self):
		while True:
			msg_queue = self.download_queue.get()
			if msg_queue is None:
				break
			uri = msg_queue.get_img_url()
			img_dir = msg_queue.get_img_dir()

			if not os.path.exists(img_dir):
				r = requests.get(uri, stream=True)
				if r.status_code == 200:
					with open(img_dir, 'wb') as f:
						for chunk in r:
							f.write(chunk)

			try:
				r = requests.get(uri)
			except (
					requests.exceptions.Timeout,
					requests.exceptions.ConnectionError,
					Exception,
					socket.timeout,
					urllib3.exceptions.ReadTimeoutError
			):
				print('Timeout occurred: ', uri)
				self.download_queue.task_done()

			if r.status_code != requests.codes.ok:
				assert False, 'Status code error: {}.'.format(r.status_code)

			with Image.open(io.BytesIO(r.content)) as im:
				filename = str(uuid.uuid4()) + '.' + im.format
				image_file_path = os.path.join(img_dir, filename.lower())
				im.save(image_file_path)

			print('Image downloaded from url: {} and saved to: {}'.format(uri, img_dir))

			self.download_queue.task_done()
