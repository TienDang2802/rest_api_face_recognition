import io
import os
import threading
import uuid

import requests
from PIL import Image


class DownloadQueue(threading.Thread):
	def __init__(self, m_queue):
		threading.Thread.__init__(self)
		self.m_queue = m_queue

	def run(self) -> None:
		while True:
			msg_queue = self.m_queue.get()
			uri = msg_queue.get_img_url()
			img_dir = msg_queue.get_img_dir()

			if not os.path.exists(img_dir):
				r = requests.get(uri, stream=True)
				if r.status_code == 200:
					with open(img_dir, 'wb') as f:
						for chunk in r:
							f.write(chunk)

			r = requests.get(uri, timeout=3.0)
			if r.status_code != requests.codes.ok:
				assert False, 'Status code error: {}.'.format(r.status_code)

			with Image.open(io.BytesIO(r.content)) as im:
				filename = str(uuid.uuid4()) + '.' + im.format
				image_file_path = os.path.join(img_dir, filename.lower())
				im.save(image_file_path)

			print('Image downloaded from url: {} and saved to: {}'.format(uri, img_dir))

			self.m_queue.task_done()