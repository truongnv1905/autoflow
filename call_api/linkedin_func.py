import os

from playwright.async_api import async_playwright

from call_api.schema import LoginRequest
from call_api.utils import config, simulate_human_behavior

SESSION_DIR = config.config['session_manager']['dir_data']


async def search_companies(data: LoginRequest):
	session_path = os.path.join(SESSION_DIR, data.username)

	async with async_playwright() as p:
		# Kiểm tra nếu user có session
		if os.path.exists(session_path):
			browser = await p.chromium.launch_persistent_context(session_path, headless=False)
		else:
			os.makedirs(session_path)  # Tạo thư mục lưu session nếu chưa có
			browser = await p.chromium.launch_persistent_context(session_path, headless=False)

		page = await browser.new_page()

		# Kiểm tra nếu chưa đăng nhập
		await page.goto('https://www.linkedin.com/feed/')
		if 'login' in page.url:
			# Tiến hành đăng nhập
			await page.goto('https://www.linkedin.com/login')
			await simulate_human_behavior(page)
			await page.fill('input[type=email]', data.username)
			await simulate_human_behavior(page)
			await page.fill('input[type=password]', data.password)
			await simulate_human_behavior(page)
			await page.click('button[type=submit]')
			await simulate_human_behavior(page)
			await page.wait_for_load_state('load')
			# Kiểm tra đăng nhập thành công

		# Tìm kiếm công ty
		search_url = f'https://www.linkedin.com/search/results/companies/?keywords={data.search_keyword}'
		await page.goto(search_url)
		await page.wait_for_selector("ul[role='list'].list-style-none", timeout=5000)

		# Lấy danh sách công ty
		company_elements = await page.query_selector_all("(//ul[@role='list'][contains(@class, 'list-style-none')])/li")

		companies = []
		for company in company_elements:
			name_element = await company.query_selector('(//span[contains(@class, "t-16")])[last()]')
			company_name = await name_element.inner_text() if name_element else 'N/A'

			location_element = await company.query_selector('//div[contains(@class, "t-14 t-black")]')
			location_text = await location_element.inner_text() if location_element else 'N/A'

			info_element = await company.query_selector('//div[contains(@class, "t-12 t-black")]')
			info_text = await info_element.inner_text() if info_element else 'N/A'

			link_element = await company.query_selector('//a[contains(@data-test-app-aware-link, "")]')
			company_url = await link_element.get_attribute('href') if link_element else 'N/A'

			companies.append({'Company Name': company_name, 'Location': location_text, 'Info': info_text, 'URL': company_url})

		await browser.close()
		return {'companies': companies}
