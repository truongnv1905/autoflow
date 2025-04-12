import logging
import os
from datetime import datetime, timedelta

from playwright.async_api import async_playwright

from call_api.schema import SearchRequestJobs
from call_api.utils import config, simulate_human_behavior

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
	logger.info(f'Starting job search for keyword: {data.search_keyword} in location: {data.location}')
	session_path = os.path.join(SESSION_DIR, data.username)
	browser = None
	try:
		async with async_playwright() as p:
			# Check if user has session
			if os.path.exists(session_path):
				logger.info(f'Using existing session at: {session_path}')
				browser = await p.chromium.launch_persistent_context(session_path, headless=False)
			else:
				logger.info(f'Creating new session at: {session_path}')
				os.makedirs(session_path)
				browser = await p.chromium.launch_persistent_context(session_path, headless=False)

			page = await browser.new_page()
			logger.info('Browser page created successfully')

			# Navigate to Google Jobs
			try:
				await simulate_human_behavior(page)
				search_keyword = f'{data.search_keyword} in {data.location}'
				search_url = f'https://www.google.com/search?q={search_keyword}&ibp=htl;jobs'
				logger.info(f'Navigating to search URL: {search_url}')
				await page.goto(search_url)
				await page.wait_for_selector('div[role="main"]', timeout=5000)

				jobs = []
				page_number = 1
				max_jobs = data.numbers
				logger.info(f'Starting job collection with max jobs limit: {max_jobs}')

				while True:
					if len(jobs) >= max_jobs:
						logger.info(f'Reached maximum job limit of {max_jobs}')
						break

					try:
						last_scroll_height = await page.evaluate('document.body.scrollHeight')
						await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
						await simulate_human_behavior(page)
						await page.wait_for_timeout(2000)
						new_scroll_height = await page.evaluate('document.body.scrollHeight')

						if new_scroll_height == last_scroll_height:
							logger.info('Reached bottom of page - No more content to load')
							break

						await page.wait_for_selector('div[data-id="jobs-detail-viewer"] div[jscontroller]', timeout=5000)
						job_elements = await page.query_selector_all('div[data-id="jobs-detail-viewer"] div[jscontroller]')
						logger.info(f'Found {len(job_elements)} job elements on current page')

						if not job_elements:
							logger.info('No job elements found on current page')
							break

						for job in job_elements:
							try:
								if len(jobs) >= max_jobs:
									break

								title_element = await job.query_selector('div[class*="tNxQIb PUpOsf"]')
								if title_element is None:
									logger.warning('Title element not found for a job')
									continue
								title = await title_element.inner_text() if title_element else ''

								company_element = await job.query_selector('div[class*="wHYlTd MKCbgd a3jPc"]')
								company = await company_element.inner_text() if company_element else ''

								location_element = await job.query_selector('div[class*="wHYlTd FqK3wc MKCbgd"]')
								location = await location_element.inner_text() if location_element else ''

								logger.info(f'Processing job: {title} at {company} in {location}')

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
										logger.error(f'Error processing time info: {str(e)}')
										info_time = 100

								# Calculate actual posted date
								posted_date = datetime.now() - timedelta(days=info_time)
								formatted_date = posted_date.strftime('%Y-%m-%d')

								job = {
									'JobTitle': data.search_keyword,
									'Location': location,
									'Title': title,
									'URL': '',
									'Source': '',
									'PostedDate': formatted_date,
									'Snippet': '',
									'CompanyName': company,
								}
								if title != '' and info_time <= data.days_ago:
									try:
										logger.info(f'Clicking on company element for job: {title}')
										await company_element.click()
										await simulate_human_behavior(page)
										await page.wait_for_timeout(1000)

										company_details = await page.query_selector('div[class*="NgUYpe"]')
										if company_details:
											jobs_decriptions_element = await company_details.query_selector(
												'span[class*="hkXmid"]'
											)
											jobs_decriptions = (
												await jobs_decriptions_element.inner_text() if jobs_decriptions_element else ''
											)

											url_jd_element = await page.query_selector(
												'a[class*="nNzjpf-cS4Vcb-PvZLI-Ueh9jd-LgbsSe-Jyewjb-tlSJBe"]'
											)
											url_jd = await url_jd_element.get_attribute('href') if url_jd_element else ''

											logger.info(f'Successfully extracted job details for: {title}')
											job['Snippet'] = jobs_decriptions
											job['URL'] = url_jd
											# Extract domain name from URL
											if url_jd and 'https://' in url_jd:
												domain = url_jd.split('https://')[1].split('.')[0]
												job['Source'] = domain
											else:
												job['Source'] = ''
									except Exception as e:
										logger.error(f'Error processing job details: {str(e)}')
										continue

									if job not in jobs:
										jobs.append(job)
										logger.info(f'Added new job to results. Total jobs collected: {len(jobs)}')

							except Exception as e:
								logger.error(f'Error processing job: {str(e)}')
								continue

					except Exception as e:
						logger.error(f'Error during page processing: {str(e)}')
						break

				logger.info(f'Job search completed. Found {len(jobs)} jobs')
				return {
					'jobs': jobs,
					'total_pages': page_number,
					'total_jobs': len(jobs),
					'limit_reached': len(jobs) >= max_jobs,
					'status': 'success',
				}

			except Exception as e:
				logger.error(f'Error during navigation: {str(e)}')
				return {
					'jobs': [],
					'total_pages': 0,
					'total_jobs': 0,
					'limit_reached': False,
					'status': 'error',
					'error_message': str(e),
				}

	except Exception as e:
		logger.error(f'Error during browser setup: {str(e)}')
		return {'jobs': [], 'total_pages': 0, 'total_jobs': 0, 'limit_reached': False, 'status': 'error', 'error_message': str(e)}

	finally:
		if browser:
			try:
				await browser.close()
				logger.info('Browser closed successfully')
			except Exception as e:
				logger.error(f'Error closing browser: {str(e)}')
