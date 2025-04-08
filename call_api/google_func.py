import os

from playwright.async_api import async_playwright

from call_api.schema import SearchRequestJobs
from call_api.utils import config, simulate_human_behavior

SESSION_DIR = config.config['session_manager']['dir_data']


async def searching_jobs(data: SearchRequestJobs):
	"""
	Search for jobs on Google Jobs with location and time filters

	Args:
		data: SearchRequest object containing search parameters
		location: Location to search in (e.g. "Ho Chi Minh City")
		time_period: Time period filter (e.g. "day", "week", "month")

	Returns:
		Dict containing job listings and metadata
	"""
	session_path = os.path.join(SESSION_DIR, data.username)
	browser = None
	try:
		async with async_playwright() as p:
			# Check if user has session
			if os.path.exists(session_path):
				browser = await p.chromium.launch_persistent_context(session_path, headless=False)
			else:
				os.makedirs(session_path)
				browser = await p.chromium.launch_persistent_context(session_path, headless=False)

			page = await browser.new_page()

			# Navigate to Google Jobs
			try:
				await simulate_human_behavior(page)
				search_keyword = f'{data.search_keyword} in {data.location}'
				search_url = f'https://www.google.com/search?q={search_keyword}&ibp=htl;jobs'
				await page.goto(search_url)
				await page.wait_for_selector('div[role="main"]', timeout=5000)

				jobs = []
				page_number = 1
				max_jobs = data.numbers  # Using max_companies as max_jobs limit

				while True:
					# Check if we've reached the job limit
					if len(jobs) >= max_jobs:
						break

					try:
						# Kiểm tra scroll
						last_scroll_height = await page.evaluate('document.body.scrollHeight')
						await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
						await simulate_human_behavior(page)

						# Đợi để trang load thêm nội dung mới
						await page.wait_for_timeout(2000)

						# Kiểm tra chiều cao mới
						new_scroll_height = await page.evaluate('document.body.scrollHeight')

						# Nếu chiều cao không thay đổi, nghĩa là đã đến cuối trang
						if new_scroll_height == last_scroll_height:
							print('Reached bottom of page - No more content to load')
							break

						# Wait for job listings to load
						await page.wait_for_selector('div[data-id="jobs-detail-viewer"] div[jscontroller]', timeout=5000)
						await simulate_human_behavior(page)

						# Get all job listings on the current page
						job_elements = await page.query_selector_all('div[data-id="jobs-detail-viewer"] div[jscontroller]')

						# If no jobs found, break the loop
						if not job_elements:
							break

						for job in job_elements:
							try:
								# Check if we've reached the job limit
								if len(jobs) >= max_jobs:
									break

								# Get job title
								title_element = await job.query_selector('div[class*="tNxQIb PUpOsf"]')
								if title_element is None:
									continue
								title = await title_element.inner_text() if title_element else ''

								# Get company name
								company_element = await job.query_selector('div[class*="wHYlTd MKCbgd a3jPc"]')
								company = await company_element.inner_text() if company_element else ''

								# Get location
								location_element = await job.query_selector('div[class*="wHYlTd FqK3wc MKCbgd"]')
								location = await location_element.inner_text() if location_element else ''

								info_element = await job.query_selector('div[class*="ApHyTb ncqQR"]')

								info_time = 100
								if info_element:
									try:
										span_element = await info_element.query_selector('span[aria-label*="Ngày đăng"]')
										if span_element:
											# Lấy nội dung của span
											text = await span_element.text_content()
											if text:  # Check if text is not None
												info_time_split = text.split(' ')
												if info_time_split[1] == 'giờ' or info_time_split[1] == 'hours':
													info_time = 1
												elif info_time_split[1] == 'ngày' or info_time_split[1] == 'days':
													info_time = int(info_time_split[0])
									except Exception as e:
										print(f'Error processing time info: {str(e)}')
										info_time = 100

								job = {
									'Title': title,
									'Company': company,
									'Location': location,
									'TimeAgo': info_time,
									'Jobs_Decriptstion': '',
									'URL_Jobs': '',
								}
								if title != '' and info_time <= data.days_ago:
									# try:
									# Click vào company element
									await company_element.click()
									await simulate_human_behavior(page)
									await page.wait_for_timeout(1000)  # Đợi content load

									# Lấy thông tin về công ty
									company_details = await page.query_selector('div[class*="NgUYpe"]')
									if company_details:
										# Lấy website công ty
										jobs_decriptions_element = await company_details.query_selector('span[class*="hkXmid"]')
										jobs_decriptions = (
											await jobs_decriptions_element.inner_text() if jobs_decriptions_element else ''
										)

										# Lấy địa chỉ công ty
										url_jd_element = await page.query_selector(
											'a[class*="nNzjpf-cS4Vcb-PvZLI-Ueh9jd-LgbsSe-Jyewjb-tlSJBe"]'
										)
										url_jd = await url_jd_element.get_attribute('href') if url_jd_element else ''

										job['Jobs_Decriptstion'] = jobs_decriptions
										job['URL_Jobs'] = url_jd
									# except:
									# 	pass
									if job not in jobs:
										jobs.append(job)

							except Exception as e:
								print(f'Error processing job: {str(e)}')
								continue

					except Exception as e:
						print(f'Error during page processing: {str(e)}')
						break

				return {
					'jobs': jobs,
					'total_pages': page_number,
					'total_jobs': len(jobs),
					'limit_reached': len(jobs) >= max_jobs,
					'status': 'success',
				}

			except Exception as e:
				print(f'Error during navigation: {str(e)}')
				return {
					'jobs': [],
					'total_pages': 0,
					'total_jobs': 0,
					'limit_reached': False,
					'status': 'error',
					'error_message': str(e),
				}

	except Exception as e:
		print(f'Error during browser setup: {str(e)}')
		return {'jobs': [], 'total_pages': 0, 'total_jobs': 0, 'limit_reached': False, 'status': 'error', 'error_message': str(e)}

	finally:
		if browser:
			try:
				await browser.close()
			except Exception as e:
				print(f'Error closing browser: {str(e)}')
