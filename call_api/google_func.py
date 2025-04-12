import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict
from urllib.parse import quote

from playwright.async_api import async_playwright

from call_api.schema import SearchRequestJobs
from call_api.utils import config, simulate_human_behavior

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[logging.FileHandler('google_jobs_search.log'), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

SESSION_DIR = config.config['session_manager']['dir_data']


def log_timing(start_time: float, operation: str) -> float:
	"""Helper function to log timing information"""
	elapsed = time.time() - start_time
	logger.info(f'{operation} time: {elapsed:.2f} seconds')
	return elapsed


async def searching_jobs(data: SearchRequestJobs) -> Dict[str, Any]:
	"""
	Search for jobs on Google Jobs with location and time filters

	Args:
	    data: SearchRequest object containing search parameters
	    location: Location to search in (e.g. "Ho Chi Minh City")
	    time_period: Time period filter (e.g. "day", "week", "month")

	Returns:
	    Dict containing job listings and metadata
	"""
	start_time = time.time()
	logger.info(f'Starting job search for keyword: {data.search_keyword} in location: {data.location}')
	session_path = os.path.join(SESSION_DIR, data.username)
	browser = None
	try:
		async with async_playwright() as p:
			# Check if user has session
			session_start = time.time()
			if os.path.exists(session_path):
				logger.info(f'Using existing session at: {session_path}')
				browser = await p.chromium.launch_persistent_context(session_path, headless=False)
			else:
				logger.info(f'Creating new session at: {session_path}')
				os.makedirs(session_path)
				browser = await p.chromium.launch_persistent_context(session_path, headless=False)
			session_time = log_timing(session_start, 'Session setup')

			page = await browser.new_page()
			logger.info('Browser page created successfully')

			# Navigate to Google Jobs
			try:
				navigation_start = time.time()
				await simulate_human_behavior(page)
				search_keyword = f'{data.search_keyword} in {data.location}'
				search_url = f'https://www.google.com/search?q={search_keyword}&ibp=htl;jobs'
				logger.info(f'Navigating to search URL: {search_url}')
				await page.goto(search_url)
				await page.wait_for_selector('div[role="main"]')
				navigation_time = log_timing(navigation_start, 'Navigation')

				jobs = []
				page_number = 1
				max_jobs = data.numbers
				total_page_time = 0
				total_job_processing_time = 0
				logger.info(f'Starting job collection with max jobs limit: {max_jobs}')

				while True:
					if len(jobs) >= max_jobs:
						logger.info(f'Reached maximum job limit of {max_jobs}')
						break

					try:
						page_start_time = time.time()
						last_scroll_height = await page.evaluate('document.body.scrollHeight')
						await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
						await simulate_human_behavior(page)
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

						job_processing_start = time.time()
						for job in job_elements:
							try:
								if len(jobs) >= max_jobs:
									break

								job_start_time = time.time()
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
											text = await span_element.text_content()
											if text:
												info_time_split = text.split(' ')
												if info_time_split[1] == 'giờ' or info_time_split[1] == 'hours':
													info_time = 1
												elif info_time_split[1] == 'ngày' or info_time_split[1] == 'days':
													info_time = int(info_time_split[0])
									except Exception as e:
										logger.error(f'Error processing time info: {str(e)}')
										info_time = 100

								posted_date = datetime.now() - timedelta(days=info_time)
								formatted_date = posted_date.strftime('%Y-%m-%d')

								job_data = {
									'JobTitle': data.search_keyword,
									'LocationDetail': location,
									'Location': data.location,
									'Title': title,
									'URL': '',
									'Source': '',
									'PostedDate': formatted_date,
									'Snippet': '',
									'CompanyName': company,
								}

								if title != '' and info_time <= data.days_ago:
									try:
										if company_element is not None:
											logger.info(f'Clicking on company element for job: {title}')
											await company_element.click()
											await simulate_human_behavior(page)

											company_details = await page.query_selector('div[class*="NgUYpe"]')
											if company_details:
												jobs_decriptions_element = await company_details.query_selector(
													'span[class*="hkXmid"]'
												)
												jobs_decriptions = (
													await jobs_decriptions_element.inner_text()
													if jobs_decriptions_element
													else ''
												)

												url_jd_element = await page.query_selector(
													'a[class*="nNzjpf-cS4Vcb-PvZLI-Ueh9jd-LgbsSe-Jyewjb-tlSJBe"]'
												)
												url_jd = await url_jd_element.get_attribute('href') if url_jd_element else ''

												logger.info(f'Successfully extracted job details for: {title}')
												job_data['Snippet'] = jobs_decriptions
												job_data['URL'] = url_jd if url_jd else ''
												if url_jd and 'https://' in url_jd:
													domain = url_jd.split('https://')[1].split('.')[0]
													job_data['Source'] = domain
												else:
													job_data['Source'] = ''
									except Exception as e:
										logger.error(f'Error processing job details: {str(e)}')
										continue

									if job_data not in jobs:
										jobs.append(job_data)
										logger.info(f'Added new job to results. Total jobs collected: {len(jobs)}')

								job_time = log_timing(job_start_time, 'Individual job processing')

							except Exception as e:
								logger.error(f'Error processing job: {str(e)}')
								continue

						job_processing_time = log_timing(job_processing_start, f'Total job processing for page {page_number}')

					except Exception as e:
						logger.error(f'Error during page processing: {str(e)}')
						break

					page_time = log_timing(page_start_time, f'Page {page_number} total')
					total_page_time += page_time
					page_number += 1

				end_time = time.time()
				total_time = end_time - start_time
				avg_page_time = total_page_time / (page_number - 1) if page_number > 1 else 0
				avg_job_time = total_job_processing_time / len(jobs) if jobs else 0

				logger.info(f'Search completed. Total time: {total_time:.2f} seconds')
				logger.info(f'Average page processing time: {avg_page_time:.2f} seconds')
				logger.info(f'Average job processing time: {avg_job_time:.2f} seconds')
				logger.info(f'Total jobs found: {len(jobs)}')
				logger.info(f'Total pages processed: {page_number}')

				return {
					'jobs': jobs,
					'total_pages': page_number,
					'total_jobs': len(jobs),
					'limit_reached': len(jobs) >= max_jobs,
					'status': 'success',
					'timing': {
						'total_time': total_time,
						'session_time': session_time,
						'navigation_time': navigation_time,
						'total_page_time': total_page_time,
						'avg_page_time': avg_page_time,
						'total_job_processing_time': total_job_processing_time,
						'avg_job_time': avg_job_time,
					},
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


async def search_company_linkedin(username: str, password: str, company_name: str, location: str) -> Dict[str, Any]:
	"""
	Search for a company's LinkedIn profile using Google search and get company details

	Args:
	    username: Username for authentication
	    password: Password for authentication
	    company_name: Name of the company to search for
	    location: Location of the company

	Returns:
	    dict: Company details including LinkedIn URL, website, email, phone and CEO information
	"""
	start_time = time.time()
	logger.info(f'Starting LinkedIn profile search for company: {company_name} in {location}')
	logger.info(f'Using credentials - Username: {username}')

	session_path = os.path.join(SESSION_DIR, username)
	browser = None
	try:
		logger.info('Initializing Playwright browser')
		async with async_playwright() as p:
			# Check if user has session
			session_start = time.time()
			if os.path.exists(session_path):
				logger.info(f'Using existing session at: {session_path}')
				browser = await p.chromium.launch_persistent_context(
					session_path,
					headless=False,
					args=[
						'--disable-blink-features=AutomationControlled',
						'--disable-infobars',
						'--disable-notifications',
						'--disable-popup-blocking',
						'--disable-extensions',
						'--disable-save-password-bubble',
						'--disable-single-click-autofill',
						'--disable-translate',
						'--disable-web-security',
						'--no-sandbox',
						'--disable-setuid-sandbox',
						'--disable-dev-shm-usage',
						'--disable-accelerated-2d-canvas',
						'--disable-gpu',
						'--window-size=1920,1080',
						'--start-maximized',
					],
					ignore_default_args=['--enable-automation'],
					viewport={'width': 1920, 'height': 1080},
					user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
					locale='en-US',
				)
			else:
				logger.info(f'Creating new session at: {session_path}')
				os.makedirs(session_path)
				browser = await p.chromium.launch_persistent_context(
					session_path,
					headless=False,
					args=[
						'--disable-blink-features=AutomationControlled',
						'--disable-infobars',
						'--disable-notifications',
						'--disable-popup-blocking',
						'--disable-extensions',
						'--disable-save-password-bubble',
						'--disable-single-click-autofill',
						'--disable-translate',
						'--disable-web-security',
						'--no-sandbox',
						'--disable-setuid-sandbox',
						'--disable-dev-shm-usage',
						'--disable-accelerated-2d-canvas',
						'--disable-gpu',
						'--window-size=1920,1080',
						'--start-maximized',
					],
					ignore_default_args=['--enable-automation'],
					viewport={'width': 1920, 'height': 1080},
					user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
					locale='en-US',
				)
				page = await browser.new_page()
				await page.goto('https://www.linkedin.com/feed/')
				if 'login' in page.url:
					await page.goto('https://www.linkedin.com/login')
					await simulate_human_behavior(page)
					await page.fill('input[type=email]', username)
					await simulate_human_behavior(page)
					await page.fill('input[type=password]', password)
					await simulate_human_behavior(page)
					await page.click('button[type=submit]')
			session_time = log_timing(session_start, 'Session setup')

			logger.info('Creating new browser page')
			page = await browser.new_page()

			# Set English language preference
			await page.set_extra_http_headers({'Accept-Language': 'en-US,en;q=0.9'})

			logger.info('Browser page created successfully')

			try:
				# Construct search query
				search_start = time.time()
				search_query = f'{company_name} {location} linkedin company profile'
				encoded_query = quote(search_query)
				search_url = f'https://www.google.com/search?q={encoded_query}&hl=en'
				logger.info(f'Constructed search query: {search_query}')
				logger.info(f'Encoded search query: {encoded_query}')
				logger.info(f'Navigating to search URL: {search_url}')

				logger.info('Loading Google search page')
				await page.goto(search_url)
				logger.info('Waiting for main content to load')
				await page.wait_for_selector('div[role="main"]')
				logger.info('Simulating human behavior')
				search_time = log_timing(search_start, 'Google search')

				# Look for LinkedIn URLs in search results
				linkedin_url = ''
				logger.info('Searching for LinkedIn URLs in results')
				search_results = await page.query_selector_all('a[href*="linkedin.com/company"]')
				logger.info(f'Found {len(search_results)} potential LinkedIn links')

				if search_results:
					logger.info('Processing LinkedIn links')
					for idx, result in enumerate(search_results, 1):
						logger.info(f'Processing link {idx}/{len(search_results)}')
						href = await result.get_attribute('href')
						if href and 'linkedin.com/company' in href:
							# Extract the actual LinkedIn URL from Google's redirect
							linkedin_url = href.split('url=')[1].split('&')[0] if 'url=' in href else href
							logger.info(f'Found valid LinkedIn URL: {linkedin_url}')
							break
						else:
							logger.info(f'Link {idx} is not a valid LinkedIn company URL')

				if not linkedin_url:
					logger.warning('No valid LinkedIn company URL found in search results')
					return {
						'CompanyName': company_name,
						'linkedin_url': '',
						'website': '',
						'email': '',
						'phone': '',
						'CEOLinkedin': '',
						'CTOLinkedin': '',
						'CFOLinkedin': '',
						'HeadOfEngineering_linkedin': '',
						'error': 'Could not find LinkedIn URL',
					}
				result = {
					'CompanyName': company_name,
					'linkedin_url': linkedin_url,
					'website': '',
					'email': '',
					'phone': '',
					'CEO': '',
					'CTO': '',
					'CFO': '',
					'HeadOfEngineering': '',
					'error': None,
				}

				# Navigate to LinkedIn company page
				logger.info(f'Navigating to LinkedIn company page: {linkedin_url}')
				linkedin_url_people = linkedin_url + '/people/?lang=en'
				await page.goto(linkedin_url_people)
				await simulate_human_behavior(page)

				# Get CEO information
				try:
					logger.info('Looking for CEO information')
					# Click on "People" tab
					# Search for CEO
					logger.info('Waiting for search input to appear')
					await page.wait_for_selector('textarea.org-people__search-input', timeout=5000)

					for text in ['CEO', 'CTO', 'CFO', 'HeadofEngineering']:
						# Check and click the button first using exact class structure
						logger.info('Checking for search button')
						button_selector = 'button.artdeco-button.artdeco-button--tertiary.artdeco-button--2.artdeco-button--muted[type="button"]'
						search_button = await page.query_selector(button_selector)

						if search_button:
							logger.info('Found search button, clicking it')
							await search_button.click()
							await simulate_human_behavior(page)
						else:
							logger.warning('Search button not found')

						search_input = await page.query_selector('textarea.org-people__search-input')
						if search_input:
							logger.info(f'Search input found, filling in {text} keyword')
							await search_input.fill(text)
							logger.info('Pressing Enter to search')
							await page.keyboard.press('Enter')
							await page.wait_for_timeout(2000)

							# Wait for search results and get first profile
							logger.info('Waiting for search results')
							await page.wait_for_selector(
								'li.grid.grid__col--lg-8.block.org-people-profile-card__profile-card-spacing', timeout=5000
							)
							# Get first profile link
							first_profile = await page.query_selector(
								'li.grid.grid__col--lg-8.block.org-people-profile-card__profile-card-spacing a[href*="/in/"]'
							)
							if first_profile:
								profile_url = await first_profile.get_attribute('href')
								if profile_url:
									result[text] = profile_url
									logger.info(f'Found {text} LinkedIn: {result[text]}')
								else:
									logger.warning('Profile URL not found in first result')
							else:
								logger.warning('No profile results found')
				except Exception as e:
					logger.error(f'Error getting {text} information: {str(e)}')

				end_time = time.time()
				total_time = end_time - start_time
				logger.info(f'Company search completed. Total time: {total_time:.2f} seconds')

				return {**result, 'timing': {'total_time': total_time, 'session_time': session_time, 'search_time': search_time}}

			except Exception as e:
				logger.error(f'Error during LinkedIn search: {str(e)}')
				logger.error(f'Error details: {type(e).__name__}')
				return {
					'CompanyName': company_name,
					'linkedin_url': '',
					'website': '',
					'email': '',
					'phone': '',
					'CEOLinkedin': '',
					'CTOLinkedin': '',
					'CFOLinkedin': '',
					'HeadOfEngineering_linkedin': '',
					'error': str(e),
				}

	except Exception as e:
		logger.error(f'Error during browser setup: {str(e)}')
		logger.error(f'Error details: {type(e).__name__}')
		return {
			'CompanyName': company_name,
			'linkedin_url': '',
			'website': '',
			'email': '',
			'phone': '',
			'CEOLinkedin': '',
			'CTOLinkedin': '',
			'CFOLinkedin': '',
			'HeadOfEngineering_linkedin': '',
			'error': str(e),
		}
	finally:
		if browser:
			try:
				logger.info('Closing browser')
				await browser.close()
				logger.info('Browser closed successfully')
			except Exception as e:
				logger.error(f'Error closing browser: {str(e)}')
				logger.error(f'Error details: {type(e).__name__}')
