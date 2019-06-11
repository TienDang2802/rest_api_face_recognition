class ImageQueueMessage(object):
	def __init__(self, img_url: str, img_dir):
		self.img_url = img_url
		self.img_dir = img_dir

	def get_img_url(self):
		return self.img_url

	def get_img_dir(self):
		return self.img_dir
