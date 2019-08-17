import os
import urllib.request
from urllib import parse
from urllib.error import HTTPError
from concurrent.futures import ThreadPoolExecutor
from os.path import basename
import mimetypes

MAX_WORKERS = 6


class DownloadImageService(object):
	def __init__(self, img_directory, redis_client, is_check_tag=False):
		self.img_directory = img_directory
		self.redis_client = redis_client
		self.is_check_tag = is_check_tag

		if not os.path.exists(img_directory):
			os.makedirs(img_directory)

	def do_download(self, uris):
		with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
			result = list(executor.map(self.download_image, uris, timeout=60))

		return list(filter(None, result))

	def download_image(self, image_url):
		try:
			response = urllib.request.urlopen(image_url)
			meta = response.info()
			img_size = meta.get(name="content-length")

			if img_size is None or int(img_size) < 10000:
				print('>>> File size < 10mb or None. Skipped :' + image_url)
				return None

			# SRC
			if self.is_check_tag:
				try:
					query_def = parse.parse_qs(parse.urlparse(image_url).query)['tag'][0]
					query_def_list = query_def.split('-')
					img_name_tag = '-'.join([query_def_list[0], query_def_list[-1]])

					extension = mimetypes.guess_extension(meta.get(name="content-type"))
					directory_img = self.img_directory + '/' + "{}{}".format(img_name_tag, extension)
				except KeyError:
					img = basename(response.url)
					directory_img = self.img_directory + '/' + img.split('?')[0]
			else:
				img = basename(response.url)
				directory_img = self.img_directory + '/' + img.split('?')[0]

			print("Downloading Image url: ", image_url)
			urllib.request.urlretrieve(image_url, directory_img)

			# Set cache img URL
			self.redis_client.set(image_url, directory_img, ex=3600)

			return directory_img
		except FileNotFoundError as err:
			print('>>> File not found:' + directory_img)
			print(err)  # something wrong with local path
			return None
		except HTTPError as err:
			print('>>> Download img error:' + image_url)
			print(err)  # something wrong with url
			return None
