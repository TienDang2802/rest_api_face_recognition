import os
import hashlib
import time
import urllib.request
from urllib import parse
from urllib.error import HTTPError
from concurrent import futures
from os.path import basename
import mimetypes
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

prefix_img_url_cache = os.getenv("PREFIX_IMG_URL_CACHE")
cache_ttl = os.getenv("CACHE_TTL")

MAX_WORKERS = 20


class DownloadImageService(object):
	def __init__(self, img_directory, redis_client, is_check_tag=False):
		self.img_directory = img_directory
		self.redis_client = redis_client
		self.is_check_tag = is_check_tag

		if not os.path.exists(img_directory):
			os.makedirs(img_directory)

	def do_download(self, uris):
		with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
			try:
				result = list(executor.map(self.download_image, uris, timeout=60))
			except futures.TimeoutError:
				print('>>>> TimeoutError')
				pass

		return list(filter(None, result))

	def download_image(self, image_url):
		try:
			response = urllib.request.urlopen(image_url)
			meta = response.info()

			img_size = meta.get(name="content-length")

			if img_size is not None and int(img_size) < 1000:
				print('>>> File size < 1mb. Skipped :' + image_url)
				return None

			# SRC
			if self.is_check_tag:
				try:
					query_def = parse.parse_qs(parse.urlparse(image_url).query)['tag'][0]
					query_def_list = hashlib.md5(query_def.encode())
					img_name_tag = query_def_list.hexdigest()

					extension = mimetypes.guess_extension(meta.get(name="content-type"))
					print('>>> extension')
					print(extension)
					if extension in ['.jpe', '.jif', '.jfif', '.jfi']:
						extension = '.jpeg'

					img_name = "{}{}".format(img_name_tag, extension)
					directory_img = self.img_directory + '/' + img_name

					if self.redis_client.exists(prefix_img_url_cache + img_name):
						return self.redis_client.get(prefix_img_url_cache + img_name)

				except KeyError:
					img = basename(response.url)
					img_name = img.split('?')[0]
					directory_img = self.img_directory + '/' + img_name

				# Set cache img URL
				self.redis_client.set(prefix_img_url_cache + img_name, directory_img, ex=cache_ttl)
			else:
				img = basename(response.url)
				img_name = img.split('?')[0]
				directory_img = self.img_directory + '/' + img_name

			print("Downloading Image url: ", image_url)
			urllib.request.urlretrieve(image_url, directory_img)

			return directory_img
		except FileNotFoundError as err:
			print('>>> File not found:' + directory_img)
			print(err)  # something wrong with local path
			return None
		except HTTPError as err:
			print('>>> Download img error:' + image_url)
			print(err)  # something wrong with url
			return None
