import logging
import os
import time
import traceback
from datetime import datetime, timedelta

import agentql
from playwright.async_api import async_playwright

from call_api.schema import SearchPeopleRequest, SearchRequestCompanies, SearchRequestJobs
from call_api.utils import config, simulate_human_behavior

SESSION_DIR = config.config['session_manager']['dir_data']

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[logging.FileHandler('linkedin_jobs_search.log'), logging.StreamHandler()],
)


async def search_companies(data: SearchRequestCompanies):
	session_path = os.path.join(SESSION_DIR, data.username)

	async with async_playwright() as p:
		# Kiểm tra nếu user có session
		if os.path.exists(session_path):
			browser = await p.chromium.launch_persistent_context(
				session_path,
				headless=False,
				user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
				locale='vi-VN',
				viewport={'width': 1366, 'height': 768},
				args=[
					'--disable-blink-features=AutomationControlled',
					'--disable-infobars',
					'--disable-notifications',
					'--disable-popup-blocking',
					'--disable-extensions',
				],
			)
		else:
			os.makedirs(session_path)  # Tạo thư mục lưu session nếu chưa có
			browser = await p.chromium.launch_persistent_context(
				session_path,
				headless=False,
				user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
				locale='vi-VN',
				viewport={'width': 1366, 'height': 768},
				# proxy=load_proxy(),
				args=[
					'--disable-blink-features=AutomationControlled',
					'--disable-infobars',
					'--start-maximized',
					'--no-default-browser-check',
					'--no-first-run',
					'--disable-dev-shm-usage',
					'--disable-gpu',
					'--disable-extensions',
				],
			)

		page = await agentql.wrap_async(browser.new_page())
		# await page.set_extra_http_headers(
		# 	{
		# 		'accept-language': 'vi-VN,vi;q=0.9',
		# 		'accept-encoding': 'gzip, deflate, br',
		# 		'referer': 'https://www.linkedin.com',
		# 		'upgrade-insecure-requests': '1',
		# 		'sec-fetch-user': '?1',
		# 		'sec-fetch-site': 'same-origin',
		# 	}
		# )
		# await page.add_init_script("""
		# 		Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
		# 		Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi'] });
		# 		Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
		# 		window.chrome = { runtime: {} };
		# 	""")
		page1 = await agentql.wrap_async(browser.new_page())
		# await page1.set_extra_http_headers(
		# 	{
		# 		'accept-language': 'vi-VN,vi;q=0.9',
		# 		'accept-encoding': 'gzip, deflate, br',
		# 		'referer': 'https://www.linkedin.com',
		# 		'upgrade-insecure-requests': '1',
		# 		'sec-fetch-user': '?1',
		# 		'sec-fetch-site': 'same-origin',
		# 	}
		# )
		# await page1.add_init_script("""
		# 		Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
		# 		Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi'] });
		# 		Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
		# 		window.chrome = { runtime: {} };
		# 	""")
		# Kiểm tra nếu chưa đăng nhập
		await page.goto('https://www.linkedin.com/feed/')
		await simulate_human_behavior(page)
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
		max_companies = data.numbers  # Giới hạn số lượng công ty

		while True:
			# Kiểm tra nếu đã đạt giới hạn
			if len(companies) >= max_companies:
				break

			# Tìm kiếm công ty với số trang
			search_url = f'https://www.linkedin.com/search/results/companies/?keywords={data.search_keyword}&page={page_number}'
		await page1.goto(search_url)
		await page1.wait_for_selector("ul[role='list'].list-style-none", timeout=5000)
		await simulate_human_behavior(page1)
		# Lấy danh sách công ty
		company_elements = await page1.query_selector_all("(//ul[@role='list'][contains(@class, 'list-style-none')])/li")

		# Nếu không có kết quả, thoát vòng lặp
		if not company_elements:
			return
		company_elements = company_elements[1:-1]
		# random.shuffle(company_elements)
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
			await page1.evaluate('window.scrollTo(0, document.body.scrollHeight)')
			await simulate_human_behavior(page1)  # Thêm delay sau khi cuộn
			await page1.wait_for_load_state('load')  # Đợi cho đến khi trang load xong

			next_button = await page1.query_selector('button[aria-label="Next"]')
			if not next_button or await next_button.is_disabled():
				break

				page_number += 1
				await simulate_human_behavior(page1)  # Thêm delay giữa các trang

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
	# if not os.path.exists(session_path):
	# 	return {'error': 'No active session found. Please login first.'}

	# Define important positions to look for
	important_positions = ['CEO', 'CTO', 'CFO', 'COO', 'Director', 'Manager', 'Lead', 'Head', 'Founder', 'President']
	employees = []

	async with async_playwright() as p:
		browser = await p.chromium.launch_persistent_context(
			session_path,
			headless=False,
			user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
			locale='vi-VN',
			viewport={'width': 1366, 'height': 768},
			# proxy=load_proxy(),
			args=[
				'--disable-blink-features=AutomationControlled',
				'--disable-infobars',
				'--disable-notifications',
				'--disable-popup-blocking',
				'--disable-extensions',
			],
		)
		page = await agentql.wrap_async(browser.new_page())
		# await page.set_extra_http_headers(
		# 	{
		# 		'accept-language': 'vi-VN,vi;q=0.9',
		# 		'accept-encoding': 'gzip, deflate, br',
		# 		'referer': 'https://www.linkedin.com',
		# 		'upgrade-insecure-requests': '1',
		# 		'sec-fetch-user': '?1',
		# 		'sec-fetch-site': 'same-origin',
		# 	}
		# )
		# await page.add_init_script("""
		# 		Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
		# 		Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi'] });
		# 		Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
		# 		window.chrome = { runtime: {} };
		# 	""")
		# Kiểm tra nếu chưa đăng nhập
		if not os.path.exists(session_path):
			await page.goto('https://www.linkedin.com/feed/')
			await simulate_human_behavior(page)
			if 'login' in page.url:
				# Tiến hành đăng nhập
				await page.goto('https://www.linkedin.com/login')
				await simulate_human_behavior(page)
				await page.fill('input[type=email]', data_request.username)
				await simulate_human_behavior(page)
				await page.fill('input[type=password]', 'Thiennhi2502')
				await simulate_human_behavior(page)
				await page.click('button[type=submit]')
				await simulate_human_behavior(page)
				await page.wait_for_load_state('load')
		try:
			list_page = list(range(1, 20))
			# random.shuffle(list_page)

			for i in list_page:
				try:
					# Navigate to the search URL using company name
					company_name = data_request.company_url.strip()
					search_url = f'https://www.linkedin.com/search/results/people/?keywords={company_name}&origin=GLOBAL_SEARCH_HEADER&page={i}'
					await page.goto(search_url)
					await simulate_human_behavior(page)
				except Exception as e:
					logging.error(
						f'Error navigating to page {i}: {str(e)}\nLine: {traceback.extract_tb(e.__traceback__)[-1].lineno}'
					)
					return {'important_employees': employees}

				try:
					await page.wait_for_selector("ul[role='list'].list-style-none", timeout=5000)
				except Exception as e:
					logging.error(
						f'Error waiting for selector on page {i}: {str(e)}\nLine: {traceback.extract_tb(e.__traceback__)[-1].lineno}'
					)
					break

				employee_elements = await page.query_selector_all("(//ul[@role='list'][contains(@class, 'list-style-none')])/li")
				if not employee_elements:
					break
				# random.shuffle(employee_elements)
				for employee in employee_elements:
					try:
						# Get employee name
						name_element = await employee.query_selector('//span[contains(@class, "t-16")]')
						name = await name_element.inner_text() if name_element else 'N/A'
						name = name.split('\n')[0]
						if 'LinkedIn' in name:
							continue

						# Get employee title
						title_element = await employee.query_selector('//div[contains(@class, "t-14 t-black")]')
						title = await title_element.inner_text() if title_element else 'N/A'

						# Check if employee has an important position
						if not any(pos.lower() in title.lower() for pos in important_positions):
							continue

						# Get profile URL
						profile_link = await employee.query_selector('//a[contains(@data-test-app-aware-link, "")]')
						profile_url = await profile_link.get_attribute('href') if profile_link else 'N/A'

						# Get company name
						company = data_request.company_url.strip()

						# Visit profile to get public email if available
						email = 'N/A'
						# if profile_url and profile_url != 'N/A':
						# 	try:
						# 		await page.goto(profile_url)
						# 		await simulate_human_behavior(page)
						# 		await page.wait_for_load_state('load')

						# 		# Check if profile is accessible
						# 		access_error = await page.query_selector('text="You don\'t have access to this profile"')
						# 		if access_error:
						# 			logging.info(f'Profile not accessible for {name}')
						# 			email = "You don't have access to this profile"
						# 			# Go back to search results page
						# 			await page.goto(search_url)
						# 			await simulate_human_behavior(page)
						# 			await page.wait_for_selector("ul[role='list'].list-style-none", timeout=5000)
						# 		else:
						# 			# If profile is accessible, try to get email
						# 			contact_button = await page.query_selector('//button[contains(text(), "Contact info")]')
						# 			if contact_button:
						# 				await contact_button.click()
						# 				await simulate_human_behavior(page)
						# 				email_element = await page.query_selector('//a[contains(@href, "mailto:")]')
						# 				if email_element:
						# 					email = await email_element.inner_text()
						# 	except Exception as e:
						# 		logging.error(
						# 			f'Error accessing profile for {name}: {str(e)}\nLine: {traceback.extract_tb(e.__traceback__)[-1].lineno}'
						# 		)
						# 		email = f'Error: {str(e)}'

						employees.append(
							{'Name': name, 'Title': title, 'Company': company, 'ProfileURL': profile_url, 'Email': email}
						)
						print(f'Name: {name} - Title: {title} - URL: {profile_url} - Email: {email}')
						await simulate_human_behavior(page)
					except Exception as e:
						logging.error(
							f'Error processing employee: {str(e)}\nLine: {traceback.extract_tb(e.__traceback__)[-1].lineno}'
						)
						continue

		except Exception as e:
			logging.error(f'Error during search: {str(e)}\nLine: {traceback.extract_tb(e.__traceback__)[-1].lineno}')
		finally:
			await browser.close()
		logging.info(employees)
		return {'important_employees': employees}


async def search_jobs(data: SearchRequestJobs):
	"""
	Search for jobs on LinkedIn with various filters

	Args:
	    data: SearchRequest object containing search parameters including:
	        - username: LinkedIn username
	        - password: LinkedIn password
	        - search_keyword: Keyword to search for
	        - location: Location filter
	        - days_ago: Filter for jobs posted within X days
	        - sort_by: Sort order ('DD' for Date Descending, 'R' for Relevance)
	        - experience_levels: List of experience levels
	        - company_ids: List of LinkedIn company IDs to filter by
	        - job_types: List of job types
	        - remote: Whether to filter for remote jobs only
	        - industry_ids: List of LinkedIn industry IDs
	        sort_by="DD" - Sắp xếp theo ngày đăng (mới nhất trước)
	        "DD" - Date Descending (ngày giảm dần)
	        "R" - Relevance (độ liên quan)
	        experience_levels=[2, 3, 4] - Lọc theo cấp độ kinh nghiệm
	        1 - Internship (Thực tập)
	        2 - Entry level (Mới vào nghề)
	        3 - Associate (Cộng sự)
	        4 - Mid-Senior level (Cấp trung-cao)
	        5 - Director (Giám đốc)
	        6 - Executive (Điều hành)
	        job_types=["F", "C"] - Lọc theo loại hợp đồng
	        "F" - Full-time (Toàn thời gian)
	        "C" - Contract (Hợp đồng)
	        "P" - Part-time (Bán thời gian)
	        "T" - Temporary (Tạm thời)
	        "I" - Internship (Thực tập)
	        "V" - Volunteer (Tình nguyện)
	        remote=True - Chỉ hiển thị công việc từ xa
	        company_ids và industry_ids - Cần biết chính xác ID của công ty/ngành trên LinkedIn
	        Có thể tìm thấy trong URL hoặc thông qua API của LinkedIn
	Returns:
	    Dict containing job listings and metadata
	"""
	try:
		start_time = time.time()
		logging.info(f'Starting job search for keyword: {data.search_keyword}')
		logging.info(f'Search parameters - Location: {data.location}, Days Ago: {data.days_ago}')

		# Log additional filter parameters if provided
		if data.sort_by:
			logging.info(f'Sort by: {data.sort_by}')
		if data.experience_levels:
			logging.info(f'Experience levels: {data.experience_levels}')
		if data.company_ids:
			logging.info(f'Companies: {data.company_ids}')
		if data.job_types:
			logging.info(f'Job types: {data.job_types}')
		if data.remote:
			logging.info(f'Remote only: {data.remote}')
		if data.industry_ids:
			logging.info(f'Industries: {data.industry_ids}')

		jobs = []
		session_path = os.path.join(SESSION_DIR, data.username)

		async with async_playwright() as p:
			try:
				# Kiểm tra nếu user có session
				browser = None
				try:
					if os.path.exists(session_path):
						browser = await p.chromium.launch_persistent_context(
							session_path,
							headless=False,
							user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
							locale='en-US',
							viewport={'width': 1366, 'height': 768},
							# proxy=load_proxy(),
							args=[
								'--disable-blink-features=AutomationControlled',
								'--disable-infobars',
								'--disable-notifications',
								'--disable-popup-blocking',
								'--disable-extensions',
							],
						)
						logging.info('Using existing session')
					else:
						os.makedirs(session_path)  # Tạo thư mục lưu session nếu chưa có
						# browser = await p.chromium.launch_persistent_context(session_path, headless=False)
						browser = await p.chromium.launch_persistent_context(
							session_path,
							headless=False,
							user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
							locale='vi-VN',
							viewport={'width': 1366, 'height': 768},
							# proxy=load_proxy(),
							args=[
								'--disable-blink-features=AutomationControlled',
								'--disable-infobars',
								'--disable-notifications',
								'--disable-popup-blocking',
								'--disable-extensions',
							],
						)
						logging.info('Created new session')
				except Exception as browser_err:
					logging.error(f'Error launching browser: {str(browser_err)}')
					return {'success': False, 'message': f'Error launching browser: {str(browser_err)}', 'jobs': []}

				page = await agentql.wrap_async(browser.new_page())
				# await page.set_extra_http_headers(
				# 	{
				# 		'accept-language': 'vi-VN,vi;q=0.9',
				# 		'accept-encoding': 'gzip, deflate, br',
				# 		'referer': 'https://www.linkedin.com',
				# 		'upgrade-insecure-requests': '1',
				# 		'sec-fetch-user': '?1',
				# 		'sec-fetch-site': 'same-origin',
				# 	}
				# )
				# await page.add_init_script("""
				# 	Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
				# 	Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi'] });
				# 	Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
				# 	window.chrome = { runtime: {} };
				# """)
				page1 = await agentql.wrap_async(browser.new_page())
				# await page1.set_extra_http_headers(
				# 	{
				# 		'accept-language': 'vi-VN,vi;q=0.9',
				# 		'accept-encoding': 'gzip, deflate, br',
				# 		'referer': 'https://www.linkedin.com',
				# 		'upgrade-insecure-requests': '1',
				# 		'sec-fetch-user': '?1',
				# 		'sec-fetch-site': 'same-origin',
				# 	}
				# )
				# await page1.add_init_script("""
				# 	Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
				# 	Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi'] });
				# 	Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
				# 	window.chrome = { runtime: {} };
				# """)
				# Kiểm tra nếu chưa đăng nhập
				try:
					await page.goto('https://www.linkedin.com/feed/')
					await simulate_human_behavior(page)
					if 'login' in page.url:
						logging.info('User not logged in, attempting login')
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

						# Check if login was successful
						if 'feed' not in page.url and 'checkpoint' in page.url:
							logging.error('Login checkpoint detected. Manual verification may be required.')
							await browser.close()
							return {
								'success': False,
								'message': 'Login checkpoint detected. Manual verification may be required.',
								'jobs': [],
							}
						elif 'login' in page.url:
							logging.error('Login failed. Check username and password.')
							await browser.close()
							return {'success': False, 'message': 'Login failed. Check username and password.', 'jobs': []}

						logging.info('Login completed')
				except Exception as login_err:
					logging.error(f'Error during login: {str(login_err)}')
					if browser:
						await browser.close()
					return {'success': False, 'message': f'Error during login: {str(login_err)}', 'jobs': []}

				page_number = 1
				max_jobs = data.numbers  # Giới hạn số lượng công việc
				page_start_time = time.time()
				start_number = 0
				number_end = 0
				while True:
					try:
						# Kiểm tra nếu	 đã đạt giới hạn
						if len(jobs) >= max_jobs:
							logging.info(f'Reached maximum jobs limit: {max_jobs}')
							break

						# Xây dựng URL tìm kiếm với các filter
						search_url = f'https://www.linkedin.com/jobs/search/?keywords={data.search_keyword}&start={start_number}'

						# Thêm location filter nếu có
						if data.location:
							search_url += f'&location={data.location}'

						# Add date posted filter if specified
						if data.days_ago:
							# Chuyển đổi số ngày thành số giây (1 ngày = 86400 giây)
							seconds = data.days_ago * 86400
							search_url += f'&f_TPR=r{seconds}'
							logging.info(f'Adding date filter: Posted within last {data.days_ago} days ({seconds} seconds)')

						# Add other filters
						try:
							# Add sort by filter
							if data.sort_by:
								search_url += f'&sortBy={data.sort_by}'
								logging.info(f'Adding sort filter: {data.sort_by}')

							# Add experience level filter
							if data.experience_levels and len(data.experience_levels) > 0:
								exp_filter = ','.join(str(level) for level in data.experience_levels)
								search_url += f'&f_E={exp_filter}'
								logging.info(f'Adding experience level filter: {exp_filter}')

							# Add company filter
							if data.company_ids and len(data.company_ids) > 0:
								company_filter = ','.join(data.company_ids)
								search_url += f'&f_C={company_filter}'
								logging.info(f'Adding company filter: {company_filter}')

							# Add job type filter
							if data.job_types and len(data.job_types) > 0:
								job_type_filter = ','.join(data.job_types)
								search_url += f'&f_JT={job_type_filter}'
								logging.info(f'Adding job type filter: {job_type_filter}')

							# Add remote filter
							if data.remote:
								search_url += '&f_WT=2'  # 2 is LinkedIn's code for remote work
								logging.info('Adding remote work filter')

							# Add industry filter
							if data.industry_ids and len(data.industry_ids) > 0:
								industry_filter = ','.join(data.industry_ids)
								search_url += f'&f_I={industry_filter}'
								logging.info(f'Adding industry filter: {industry_filter}')
						except Exception as filter_err:
							logging.error(f'Error setting search filters: {str(filter_err)}')
							# Continue with basic search without filters

						logging.info(f'Searching page {page_number}: {search_url}')
						try:
							await page1.goto(search_url)
							await page1.wait_for_selector('div[class*="scaffold-layout__list"] li[id*="ember"]', timeout=10000)
							await simulate_human_behavior(page1)
						except Exception as nav_err:
							logging.error(f'Error navigating to search page: {str(nav_err)}')
							# Try a more generic selector or continue to next page
							try:
								await page1.wait_for_selector('div.jobs-search-results-list', timeout=5000)
							except:
								logging.error('Failed to find job listings, moving to next page')
								page_number += 1
								start_number += 25  # LinkedIn typically shows 25 jobs per page
								number_end += 1
								if number_end > 10:
									break

								continue

						# Lấy danh sách công việc
						job_elements = []
						try:
							job_elements = await page1.query_selector_all('div[class*="scaffold-layout__list"] li[id*="ember"]')
							start_number += len(job_elements)
							logging.info(f'Found {len(job_elements)} jobs on page {page_number}')
						except Exception as job_list_err:
							logging.error(f'Error getting job list: {str(job_list_err)}')
							try:
								# Try alternative selector
								job_elements = await page1.query_selector_all('li.jobs-search-results__list-item')
								start_number += len(job_elements)
								logging.info(f'Found {len(job_elements)} jobs using alternative selector on page {page_number}')
							except:
								logging.error('Failed to get job elements with alternative selector')

						# Nếu không có kết quả, thoát vòng lặp
						if not job_elements:
							logging.info('No more jobs found')
							break
						# random.shuffle(job_elements)
						for job in job_elements:
							try:
								# Kiểm tra nếu đã đạt giới hạn
								if len(jobs) >= max_jobs:
									break
								if job is None:
									continue

								# Initialize variables with default values
								title = 'N/A'
								company = 'N/A'
								location = 'N/A'
								posting_time = 'N/A'
								job_url = 'N/A'
								description = 'N/A'

								# Lấy tiêu đề công việc
								try:
									title_element = await job.query_selector('div[dir="ltr"] > span[aria-hidden="true"] > strong')
									if title_element:
										title = await title_element.inner_text()
										title = title.encode('utf-8', errors='ignore').decode('utf-8')
										logging.info(f'Job title: {title}')

										try:
											await title_element.click()
											await simulate_human_behavior(page1)
											logging.info('Successfully clicked on job listing')
										except Exception as click_err:
											logging.error(f'Error clicking job: {str(click_err)}')
								except Exception as title_err:
									logging.error(f'Error getting job title: {str(title_err)}')

								# Lấy tên công ty
								try:
									company_element = await job.query_selector('div[class*="subtitle"] div[dir="ltr"]')
									if company_element:
										company = await company_element.inner_text()
										company = company.encode('utf-8', errors='ignore').decode('utf-8')
										logging.info(f'Company: {company}')
								except Exception as company_err:
									logging.error(f'Error getting company: {str(company_err)}')

								# Lấy địa điểm
								try:
									location_element = await job.query_selector('div.artdeco-entity-lockup__caption')
									if location_element:
										location = await location_element.inner_text()
										location = location.encode('utf-8', errors='ignore').decode('utf-8')
										logging.info(f'Location: {location}')
								except Exception as location_err:
									logging.error(f'Error getting location: {str(location_err)}')

								# Lấy URL công việc
								try:
									link_element = await job.query_selector('a[class*="card-wrapper__card-link"]')
									if link_element:
										job_url = await link_element.get_attribute('href') or 'N/A'
										if job_url != 'N/A':
											# Ensure the URL is complete with domain
											if not job_url.startswith('http'):
												job_url = 'https://www.linkedin.com' + job_url
											logging.info(f'Found job URL: {job_url}')
								except Exception as url_err:
									logging.error(f'Error getting job URL: {str(url_err)}')

								# Lấy mô tả công việc
								try:
									description_element = await page1.query_selector(
										'div[class*="jobs-search__job-details--wrapper"]'
									)
									if description_element:
										description_element_detail = await description_element.query_selector(
											'div[class*="jobs-description__content jobs-description-content"]'
										)
										if description_element_detail:
											try:
												description = await description_element_detail.inner_text()
												description = description.encode('utf-8', errors='ignore').decode('utf-8')
												logging.info('Successfully extracted job description')
											except Exception as desc_text_err:
												logging.error(f'Error getting job description text: {str(desc_text_err)}')
												description = 'Error extracting description'
										else:
											logging.warning('Job description detail element not found')
									else:
										logging.warning('Job description wrapper element not found')
								except Exception as desc_err:
									logging.error(f'Error getting job description: {str(desc_err)}')

								# Lấy tất cả các span có class chứa "tvm__text"
								tvm_text_details = []
								try:
									tertiary_container = await page1.query_selector(
										'div.t-black--light.mt2.job-details-jobs-unified-top-card__tertiary-description-container'
									)
									if tertiary_container:
										tvm_text_elements = await tertiary_container.query_selector_all(
											'span[class*="tvm__text"]'
										)
										if tvm_text_elements:
											for span in tvm_text_elements:
												try:
													span_text = await span.inner_text()
													if span_text:
														span_text = span_text.strip()
														span_text = span_text.encode('utf-8', errors='ignore').decode('utf-8')
														tvm_text_details.append(span_text)

														# Nếu chưa có thời gian đăng, kiểm tra xem span này có chứa thông tin thời gian không
														if posting_time == 'N/A' and (
															'ago' in span_text.lower()
															or 'posted' in span_text.lower()
															or 'trước' in span_text.lower()
															or 'minutes' in span_text.lower()
															or 'hours' in span_text.lower()
															or 'days' in span_text.lower()
															or 'weeks' in span_text.lower()
															or 'phút' in span_text.lower()
															or 'giờ' in span_text.lower()
															or 'ngày' in span_text.lower()
															or 'tuần' in span_text.lower()
														):
															try:
																posting_time = span_text
																info_time_split = posting_time.split(' ')
																info_time = 0

																if 'phút' in info_time_split or 'minutes' in info_time_split:
																	info_time = 0
																elif 'giờ' in info_time_split or 'hours' in info_time_split:
																	info_time = 0  # Posted today (hours ago)
																elif 'ngày' in info_time_split or 'days' in info_time_split:
																	info_time = int(info_time_split[0])  # Adjusted index
																elif 'tuần' in info_time_split or 'weeks' in info_time_split:
																	info_time = int(info_time_split[0]) * 7  # Adjusted index
																elif 'tháng' in info_time_split or 'months' in info_time_split:
																	info_time = int(info_time_split[0]) * 30  # Adjusted index

																posted_date = datetime.now() - timedelta(days=info_time)
																posting_time = posted_date.strftime('%Y-%m-%d')
																break
															except Exception as date_parse_err:
																logging.error(f'Error parsing date: {str(date_parse_err)}')
																posting_time = datetime.now().strftime(
																	'%Y-%m-%d'
																)  # Default to today
												except Exception as span_err:
													logging.error(f'Error processing span element: {str(span_err)}')

											# logging.info(f'Found {len(tvm_text_details)} tvm__text elements: {tvm_text_details}')
										else:
											logging.warning('No span elements with class tvm__text found')
								except Exception as tvm_err:
									logging.error(f'Error extracting tvm__text elements: {str(tvm_err)}')

								# Get additional job details
								job_details = {}

								# Create job data object
								try:
									job_data = {
										'JobTitle': data.search_keyword,
										'LocationDetail': location if location and location != 'N/A' else data.location,
										'Location': data.location,
										'Title': title if title and title != 'N/A' else 'Unknown Position',
										'URL': job_url if job_url and job_url != 'N/A' else '',
										'Source': 'linkedin',
										'PostedDate': posting_time
										if posting_time and posting_time != 'N/A'
										else datetime.now().strftime('%Y-%m-%d'),
										'Snippet': description if description and description != 'N/A' else '',
										'CompanyName': company if company and company != 'N/A' else 'Unknown Company',
									}

									jobs.append(job_data)
									logging.info(f'Added job: {title} at {company}')
								except Exception as data_err:
									logging.error(f'Error creating job data: {str(data_err)}')
							except Exception as job_process_err:
								logging.error(f'Error processing job: {str(job_process_err)}')

								continue  # Skip this job and continue with the next one

						page_number += 1
						await simulate_human_behavior(page1)
					except Exception as page_err:
						logging.error(f'Error processing page {page_number}: {str(page_err)}')
						page_number += 1
						number_end += 1
						if number_end > 10:
							break
						continue  # Try next page

				await browser.close()
				end_time = time.time()
				total_time = end_time - start_time
				logging.info(f'Search completed. Total time: {total_time:.2f} seconds')
				logging.info(f'Total jobs found: {len(jobs)}')
				logging.info(f'Total pages processed: {page_number}')

				# Log additional search metadata
				metadata = {
					'total_pages': page_number,
					'total_jobs': len(jobs),
					'limit_reached': len(jobs) >= max_jobs,
					'search_time': total_time,
					'timestamp': datetime.now().isoformat(),
					'filters': {
						'sort_by': data.sort_by,
						'experience_levels': data.experience_levels,
						'company_ids': data.company_ids,
						'job_types': data.job_types,
						'remote': data.remote,
						'industry_ids': data.industry_ids,
						'days_ago': data.days_ago,
						'location': data.location,
					},
				}
				logging.info(f'Search metadata: {metadata}')

				return {'success': True, 'message': f'Found {len(jobs)} jobs for {data.search_keyword}', 'jobs': jobs}

			except Exception as e:
				logging.error(f'Error in search_jobs process: {str(e)}')
				if 'browser' in locals() and browser:
					await browser.close()
				return {'success': False, 'message': f'Error in search_jobs process: {str(e)}', 'jobs': []}

	except Exception as e:
		logging.error(f'Unexpected error in search_jobs: {str(e)}')
		return {'success': False, 'message': f'Unexpected error in search_jobs: {str(e)}', 'jobs': []}
