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
	await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
	await page.wait_for_timeout(random.randint(1000, 3000))
	await page.mouse.wheel(0, random.randint(300, 700))
	await page.wait_for_timeout(random.randint(1000, 2000))
