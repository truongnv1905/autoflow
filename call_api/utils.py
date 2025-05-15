import asyncio
import random

import yaml


class AppConfig:
	def __init__(self, config_file='call_api/config.yaml'):
		self.config_file = config_file
		self.config = self.load_config()

	def load_config(self):
		with open(self.config_file, 'r', encoding='utf-8') as file:
			return yaml.safe_load(file)


config = AppConfig()


async def simulate_human_behavior(page):
	# Di chuyển chuột ngẫu nhiên
	for _ in range(random.randint(1, 3)):
		x = random.randint(0, 1200)
		y = random.randint(0, 800)
		await page.mouse.move(x, y, steps=random.randint(5, 15))
		await asyncio.sleep(random.uniform(0.3, 1.2))

	# Scroll nhẹ như người dùng
	if random.random() > 0.5:
		await page.mouse.wheel(0, random.randint(200, 800))
		await asyncio.sleep(random.uniform(0.5, 1.5))

	# Thời gian delay giữa các thao tác
	await asyncio.sleep(random.uniform(2.5, 5.0))
