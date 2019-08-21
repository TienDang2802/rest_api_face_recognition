import glob
import os
import shutil

import redis as redis
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import time

load_dotenv(find_dotenv())

redis_host = os.getenv("CNF_REDIS_HOST")
redis_port = os.getenv("CNF_REDIS_PORT")
redis_password = os.getenv("CNF_REDIS_PASS")
prefix_img_url_cache = os.getenv("PREFIX_IMG_URL_CACHE")

if __name__ == '__main__':
	redis = redis.Redis(host=redis_host, port=redis_port, password=redis_password)

	pubsub = redis.pubsub()
	pubsub.psubscribe('__keyevent@0__:expired')

	print('Starting message loop')

	while True:
		message = pubsub.get_message()
		if message:
			try:
				data = message['data']
				if isinstance(data, bytes):
					data = data.decode("utf-8")
					if data.startswith(prefix_img_url_cache):
						for item in glob.glob(
								'./uploads/images/**/*{}'.format(data.replace(prefix_img_url_cache, '')),
								recursive=True):
							if os.path.exists(item):
								dir_path = Path(item).resolve().parent.parent.absolute()
								print('>>>> Remove directory:', dir_path)
								shutil.rmtree(dir_path)
			except KeyError:
				continue
		time.sleep(0.2)
