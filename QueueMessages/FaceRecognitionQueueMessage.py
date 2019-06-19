class FaceRecognitionQueueMessage(object):
	def __init__(self, src_img, des_url: str):
		self.src_img = src_img
		self.des_url = des_url

	def get_src_img(self):
		return self.src_img

	def get_des_url(self):
		return self.des_url
