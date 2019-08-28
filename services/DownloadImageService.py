import multiprocessing
import os
import hashlib
import urllib.request
from urllib.error import HTTPError, URLError
from os.path import basename
import mimetypes
import redis
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

prefix_img_url_cache = os.getenv("PREFIX_IMG_URL_CACHE")
cache_ttl = os.getenv("CACHE_TTL")
redis_host = os.getenv("CNF_REDIS_HOST")
redis_port = os.getenv("CNF_REDIS_PORT")
redis_password = os.getenv("CNF_REDIS_PASS")

redis_client = redis.Redis(host=redis_host, port=redis_port, password=redis_password)


class DownloadImageService(object):
	def __init__(self, img_directory, is_check_tag=False):
		self.img_directory = img_directory
		self.is_check_tag = is_check_tag

		if not os.path.exists(img_directory):
			os.makedirs(img_directory)

	def do_download(self, uris):
		pool = multiprocessing.Pool(multiprocessing.cpu_count())
		result = pool.map(self.download_image, uris)

		pool.close()
		pool.join()
		pool.terminate()

		return list(filter(None, result))

	def download_image(self, image_url):
		img_name_tag = hashlib.md5(image_url.encode())
		img_name_tag = img_name_tag.hexdigest()
		key_cache = "{}{}".format(prefix_img_url_cache, img_name_tag)
		if redis_client.exists(key_cache):
			return redis_client.get(key_cache)

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
					extension = mimetypes.guess_extension(meta.get(name="content-type"))
					if extension in ['.jpe', '.jif', '.jfif', '.jfi']:
						extension = '.jpeg'

					img_name = "{}{}".format(img_name_tag, extension)
					directory_img = self.img_directory + '/' + img_name
				except KeyError:
					img = basename(response.url)
					img_name = img.split('?')[0]
					directory_img = self.img_directory + '/' + img_name

				# Set cache img URL
				redis_client.set(key_cache, directory_img, ex=cache_ttl)
			else:
				img = basename(response.url)
				img_name = img.split('?')[0]
				directory_img = self.img_directory + '/' + img_name

			try:
				urllib.request.urlretrieve(image_url, directory_img)
			except urllib.error.ContentTooShortError:
				print('Network conditions is not good. Reloading...')
				urllib.request.urlretrieve(image_url, directory_img)

			return directory_img
		except FileNotFoundError as err:
			print('>>> File not found:' + directory_img)
			print(err)  # something wrong with local path
			return None
		except (HTTPError, URLError) as err:
			print('>>> Download img error:' + image_url)
			print(err)  # something wrong with url
			return None
