import os
from queue import Queue

from QueueMessages.ImageQueueMessage import ImageQueueMessage
from queues.DownloadQueue import DownloadQueue


class DownloadImageService(object):
	NUM_FETCH_THREADS = 4

	def __init__(self, num_fetch_threads=None):
		if num_fetch_threads:
			self.num_fetch_threads = num_fetch_threads
		else:
			self.num_fetch_threads = self.NUM_FETCH_THREADS

	def do_download(self, uris, img_directory: str):
		if not os.path.exists(img_directory):
			os.makedirs(img_directory)

		download_queue = Queue()

		self.__fetch_url_src(download_queue, uris, img_directory)

		for i in range(self.num_fetch_threads):
			worker = DownloadQueue(download_queue)
			worker.setDaemon(True)
			worker.start()

		download_queue.join()
		print('Process download done')

	def __fetch_url_src(self, download_queue: Queue, uris, path_dir):
		for uri in uris:
			queue_message = ImageQueueMessage(uri, path_dir)
			download_queue.put(queue_message)