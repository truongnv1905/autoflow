import os

from playwright.async_api import async_playwright

from call_api.schema import SearchPeopleRequest, SearchRequest
from call_api.utils import config, simulate_human_behavior

SESSION_DIR = config.config['session_manager']['dir_data']


async def search_companies(data: SearchRequest):
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

		companies = []
		page_number = 1
		max_companies = data.max_companies  # Giới hạn số lượng công ty

		while True:
			# Kiểm tra nếu đã đạt giới hạn
			if len(companies) >= max_companies:
				break

			# Tìm kiếm công ty với số trang
			search_url = f'https://www.linkedin.com/search/results/companies/?keywords={data.search_keyword}&page={page_number}'
			await page.goto(search_url)
			await page.wait_for_selector("ul[role='list'].list-style-none", timeout=5000)

			# Lấy danh sách công ty
			company_elements = await page.query_selector_all("(//ul[@role='list'][contains(@class, 'list-style-none')])/li")

			# Nếu không có kết quả, thoát vòng lặp
			if not company_elements:
				break

			for company in company_elements:
				# Kiểm tra nếu đã đạt giới hạn
				if len(companies) >= max_companies:
					break

				name_element = await company.query_selector('(//span[contains(@class, "t-16")])[last()]')
				company_name = await name_element.inner_text() if name_element else 'N/A'

				location_element = await company.query_selector('//div[contains(@class, "t-14 t-black")]')
				location_text = await location_element.inner_text() if location_element else 'N/A'

				info_element = await company.query_selector('//div[contains(@class, "t-12 t-black")]')
				info_text = await info_element.inner_text() if info_element else 'N/A'

				link_element = await company.query_selector('//a[contains(@data-test-app-aware-link, "")]')
				company_url = await link_element.get_attribute('href') if link_element else 'N/A'

				companies.append(
					{
						'Company Name': company_name,
						'Location': location_text,
						'Info': info_text,
						'URL': company_url,
						'Page': page_number,
					}
				)

			# Kiểm tra nút next page
			# Cuộn trang xuống dưới để load nút Next
			await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
			await simulate_human_behavior(page)  # Thêm delay sau khi cuộn
			await page.wait_for_load_state('load')  # Đợi cho đến khi trang load xong

			next_button = await page.query_selector('button[aria-label="Next"]')
			if not next_button or await next_button.is_disabled():
				break

			page_number += 1
			await simulate_human_behavior(page)  # Thêm delay giữa các trang

		await browser.close()
		return {
			'companies': companies,
			'total_pages': page_number,
			'total_companies': len(companies),
			'limit_reached': len(companies) >= max_companies,
		}


async def get_info_employees(data_request: SearchPeopleRequest):
	session_path = os.path.join(SESSION_DIR, data_request.username)

	# Check if session exists, if not return early
	if not os.path.exists(session_path):
		return {'error': 'No active session found. Please login first.'}

	async with async_playwright() as p:
		browser = await p.chromium.launch_persistent_context(session_path, headless=False)
		page = await browser.new_page()

		# Navigate to company employees page
		if data_request.company_url.endswith('/'):
			data_request.company_url = data_request.company_url[:-1]
		employees_url = f'{data_request.company_url}/people/'
		await page.goto(employees_url)
		await page.wait_for_selector("ul[role='list'].list-style-none", timeout=5000)

		# Define important positions to look for
		important_positions = ['CEO', 'CTO', 'HR Manager', 'Head of Engineering']

		# Get all employee elements
		employee_elements = await page.query_selector_all("(//ul[@role='list'][contains(@class, 'list-style-none')])/li")

		important_employees = []
		for employee in employee_elements:
			# Get employee name and title
			name_element = await employee.query_selector('(//span[contains(@class, "t-16")])[last()]')
			title_element = await employee.query_selector('//div[contains(@class, "t-14 t-black")]')

			if name_element and title_element:
				name = await name_element.inner_text()
				title = await title_element.inner_text()

				# Check if employee has an important position
				if any(pos.lower() in title.lower() for pos in important_positions):
					# Get profile URL
					profile_link = await employee.query_selector('//a[contains(@data-test-app-aware-link, "")]')
					profile_url = await profile_link.get_attribute('href') if profile_link else 'N/A'

					# Get company name
					company_element = await employee.query_selector('//div[contains(@class, "t-12 t-black")]')
					company = await company_element.inner_text() if company_element else 'N/A'

					# Visit profile to get public email if available
					if profile_url and profile_url != 'N/A':
						await page.goto(profile_url)
						await simulate_human_behavior(page)
						await page.wait_for_load_state('load')

						# Look for email in contact info
						email = 'N/A'
						try:
							contact_button = await page.query_selector('//button[contains(text(), "Contact info")]')
							if contact_button:
								await contact_button.click()
								await simulate_human_behavior(page)
								email_element = await page.query_selector('//a[contains(@href, "mailto:")]')
								if email_element:
									email = await email_element.inner_text()
						except:
							pass

						important_employees.append(
							{'Name': name, 'Title': title, 'Company': company, 'Profile URL': profile_url, 'Email': email}
						)

						# Go back to employees page
						await page.goto(employees_url)
						await page.wait_for_selector("ul[role='list'].list-style-none", timeout=5000)

		await browser.close()
		return {'important_employees': important_employees}
