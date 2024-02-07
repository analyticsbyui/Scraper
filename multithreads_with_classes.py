from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
from xml.etree import ElementTree
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
import json
from urllib.parse import urlparse
from urllib.parse import parse_qs
import signal
import sys
from webdriver_manager.chrome import ChromeDriverManager
from urllib3.exceptions import MaxRetryError
from wakepy import set_keepawake, unset_keepawake
import traceback
import os
from concurrent.futures import ThreadPoolExecutor
import checker
import threading

scan_id=datetime.now().strftime('%d%m%Y')
pindex=1
blacklist=None


class Tester():
    def __init__(self, config, date):
        self.config = config
        self.driver = self.start_driver()
        self.date = date

    def add_identifier_to_url(self, url):
        ''' Adds an identifier to the url for potential tracking purposes.
            Returns a string.'''

        # Check for query string.
        if "?" in url:
            return url + "&analyticsIntegrationVerificationBot"
        else:
            return url + "?analyticsIntegrationVerificationBot"
        
    def get_page_visited(self, url, pages_visited):
        ''' Gets a Page object from the pages_visited list.
            Returns a Page.'''
        
        url = checker.normalize_url(url) #this might not be necessary if we normalize its inputs before calling the function

        # Get the first page that matches the provided url or has the url as alias.
        # If not found return None.
        return next((page for page in pages_visited 
                        if page.get_url() == url or 
                        url in page.get_aliases()), None)

    def process_browser_logs_for_network_events(self, logs):
        '''Filters network requests from browser logs.
            Yields a dictionary with the log information.'''
        
        for entry in logs:
            log = json.loads(entry["message"])["message"]
            if (
                "Network.response" in log["method"]
                or "Network.request" in log["method"]
                or "Network.webSocket" in log["method"]
            ):
                yield log

    def page_loaded(self, driver):
        '''Checks the ready state of the web page.
            Returns a bool.'''

        if(config['catalog']):
            
            # Confirm that document has loaded and that last update happened more 
            # than 2 seconds ago. 
            return (driver.execute_script("return document.readyState") == "complete" 
                    and driver.execute_script("return ((new Date()).getTime()-lastTime)>2000"))
        else:

            # Confirm that document has loaded.
            return driver.execute_script("return document.readyState") == "complete" 

    def test_url(self, url, urls_to_visit, pages_visited):
        '''Main logic for crawling a webpage.'''

        print(url)

        # Add identifier for potential analytic purposes.
        page_url_with_identifier = self.add_identifier_to_url(url)

        # Load the page.
        try:
            # Reset cookies after every page so they're fresh.
            self.driver.delete_all_cookies()
            self.driver.get(page_url_with_identifier)
        except (MaxRetryError, ConnectionResetError) as e:
            return
        except (Exception) as e:

            # This should ideally never happen.
            print("super broken", e)
            return
        self.count_driver_load()
        current_url = self.driver.current_url
        
        # Check if current_url has scope domain and is not
        # in the blacklist.
        if not checker.check_standard(current_url):
            self.count_check_standard()
            return
                    
        self.count_check_standard()

        # Fromat current url to standard.
        current_url = checker.normalize_url(current_url)
    
        # Replace our identifier if it exists in the link.
        current_url = checker.check_identifier(current_url)  

        # Create a Page object
        page = Page(current_url)

        self.count_page_created()

        # Handle redirects.
        if current_url != url:
            
            # A mismatching url when page loads probably means we were redirected.
            print("url mismatch. redirected?")

            # Check if current_url is in queue to visit.
            if current_url in urls_to_visit:
                urls_to_visit.remove(current_url)

            # Check if page has already been visited.
            page_visited = self.get_page_visited(current_url, pages_visited)

            # Page has been visited, no need to continue scraping.
            if page_visited != None:

                # Set page's url as alias for visited page.
                page_visited.add_alias(url)
                print("Page Already visited")
                self.count_page_already_visited()
                return
            else:

                # Add url as alias for the current Page object.
                page.add_alias(url)

        pages_visited.append(page)
        self.count_pages_visited_add()

        print(f'\n\t{os.getpid()}\n')
        print(f'\n \tCurrent page visited count {len(pages_visited)}')

        # Search for chrome error in Single Page Applications.
        try:
            elem = self.driver.find_element(By.ID, "error-information-popup-content")
            print(elem.find_element(By.CLASS_NAME, "error-code").text)
            page.error_code = elem.find_element(By.CLASS_NAME, "error-code").text

            self.count_error_found()
            # Error found. No need to continue.
            return
        except:
            pass

        # Chrome returns empty page source if page is not found 
        # while running headless.
        if "<body></body>" in self.driver.page_source:
            print("body empty")
            page.error_code = "404"
            #return

        # Check page title for 404.
        if "404" in self.driver.title:
            print("404")
            page.error_code = "404"

            ## Page not found, no need to continue.
            #return
        
        # Check page status for error status codes.
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            print(resp)
            if "404" == resp.status_code:
                print(resp.status_code)
                page.error_code = resp.status_code

                ## Page not found, no need to continue.
                #return
        except (Exception) as e:
            pass

        self.count_checked_errors()

        # Crawl the page for links.
        # Since page load is set to eager, we need to wait until everything else is 
        # loaded before checking network requests and cookies.
        self.driver.execute_script('''
            lastTime=(new Date()).getTime();
            const config = { attributes: true, childList: true, subtree: true };
            const targetNode = document.body;
            const callback = (mutationList, observer) => {lastTime=(new Date()).getTime();};
            const observer = new MutationObserver(callback);observer.observe(targetNode, config);
                                ''')
        WebDriverWait(self.driver, timeout=30).until(self.page_loaded)
        # #driver.save_screenshot(str(len(pages_visited))+'.png')

        self.count_page_fully_loaded()
        
        if self.config['crawl']:

            # Get all a tags.
            links = self.driver.find_elements(By.TAG_NAME, "a")

            for link in links:
                try:
                    link_url = link.get_attribute("href")

                    # "href" not found.
                    if link_url == None:
                        continue

                    # Not an absolute link 
                    if "://" not in link_url:
                        continue

                    # Empty string
                    if link_url.strip() == "":
                        continue

                    # Replace our identifier if it exists in the link.
                    link_url = checker.check_identifier(link_url)

                    normalized_url = checker.normalize_url(link_url)
                    if ("byui.edu" not in normalized_url and self.config["columns"]['external_links']):
                        page.add_external_link(link_url)
                    elif "byui.edu" in normalized_url:
                        page.add_link(link_url)

                    # Confirm url is not in queue to visit or already visited
                    # and perform standard validation check.
                    #duplicate = sum(map(lambda url: checker.check_duplicate(normalized_url, url), urls_to_visit))
                    if (normalized_url.lower() not in urls_to_visit
                        #and duplicate == 0 
                        and self.get_page_visited(link_url, pages_visited)== None 
                        and checker.check_standard(link_url)):
                        
                        # Check for file extensions.
                        if not any(substring in normalized_url for substring in 
                                [".pdf", ".pptx", ".ppt", ".doc", ".docx", ".xlsx", 
                                ".xls", ".xlsm", ".exe", ".zip", ".jpg", ".png", ".mp3", ".mp4"]):
                            
                            urls_to_visit.add(normalized_url.lower())
                        elif self.config['files']:
                            '''
                                CHECK WITH JOSUE TO SEE WHAT IS EXPECTED WHEN  "FILES" IS SELECTED
                            '''
                            pages_visited.append(Page(normalized_url))
                except StaleElementReferenceException:
                    pass
        self.count_crawled_page()
        
        if self.config["columns"]["title"]:
            page.title = self.driver.title
        self.count_set_title()

        # Set Page cookies from driver cookies.
        if self.config['columns']['cookies']:
            page.cookies = [cookie['name'] for cookie in self.driver.get_cookies()]
        self.count_set_cookies()

        # Check if tracking_ids was selected
        if self.config['columns']['tracking_ids']:

            logs = self.driver.get_log("performance")
            events = self.process_browser_logs_for_network_events(logs)

            # find analytics collect calls
            for event in events:
                if event['method'] == 'Network.requestWillBeSent':
                    url = event['params']['request']['url']
                    doc_url = event['params']['documentURL']
                    parsed_url = urlparse(url)
                    query_params = parse_qs(parsed_url.query)

                    # If the url the request was made for doesn't match the page 
                    # we're scanning, skip it.
                    if doc_url != self.driver.current_url:
                        continue
                    
                    # Add tracking id's to Page object.
                    if "google-analytics.com/collect" in url or "google-analytics.com/j/collect" in url:
                        page.add_tracking_id(query_params['tid'][0], "GA")

                    if "googletagmanager.com/gtm.js" in url:
                        page.add_tracking_id(query_params['id'][0], "GTM")

                    if "googletagmanager.com/gtag/js" in url:
                        page.add_tracking_id(query_params['id'][0], "GTAG")
        self.count_set_tracking_ids()

        if self.config['columns']['terms'] and not self.config['use_terms']:

            # Search if term exists in page content.
            body = self.driver.execute_script('return document.body.innerText')
            page.terms = (self.config['term'] in body)+0
        elif self.config['use_terms']:
            body = self.driver.execute_script('return document.body.innerText')

            # Use self.check_matches to find if any term in file matches page content.
            page.terms = (checker.check_terms(body))+0


        # Get the Load time of the current page with this script
        if self.config['columns']['load_time']:
            page.load_time = self.driver.execute_script(
            '''var entries = window.performance.getEntriesByType("navigation");
                if (entries.length > 0) {
                    var navTiming = entries[0];
                    var pageLoadTime = navTiming.loadEventEnd - navTiming.startTime;
                    return Math.round((pageLoadTime / 1000) * 100) / 100;
                    }''')
            
        self.finished_scrape()

    def count_driver_load(self):
        print('Override this method')
    def count_check_standard(self):
        print('Override this method')
    def count_page_created(self):
        print('Override this method')
    def count_page_already_visited(self):
        print('Override this method')
    def count_pages_visited_add(self):
        print('Override this method')
    def count_error_found(self):
        print('Override this method')
    def count_checked_errors(self):
        print('Override this method')
    def count_page_fully_loaded(self):
        print('Override this method')
    def count_crawled_page(self):
        print('Override this method')
    def count_set_title(self):
        print('Override this method')
    def count_set_cookies(self):
        print('Override this method')
    def count_set_tracking_ids(self):
        print('Override this method')
    def finished_scrape(self):
        print('Override this method')

    def start_driver(self):
        ''' Set up configurations for the selenium driver.
            Returns a driver.'''

        # This block sets up selenium settings.
        ############################################################################
        chrome_options = Options()

        # These settings are an effort to disable file downloads.
        prefs = {
            "download_restrictions": 3,
            "download.open_pdf_in_system_reader": False,
            "download.prompt_for_download": True,
            "download.default_directory": "/dev/null",
            "plugins.always_open_pdf_externally": False
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Default capabilities.
        chrome_options.capabilities.update(DesiredCapabilities.CHROME)

        # Enable logging so we can get the network logs.
        chrome_options.set_capability("goog:loggingPrefs", {'performance': 'ALL'})

        # Turn off gpu and extensions, these can cause weird problems.
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")

        # Run headless so that the chrome window stays hidden.
        chrome_options.add_argument("--enable-javascript")
        # chrome_options.add_argument("--headless")
        # if(not self.config['catalog']):
        #     chrome_options.add_argument("--headless")

        # Eager loading lets the program continue after the html is loaded, but 
        # before everthing else has finished loading we use this so we can crawl the
        # page for links before continuing on to log analytics calls.
        chrome_options.page_load_strategy = "eager"

        service = Service(executable_path=ChromeDriverManager().install())

        # Set up the webdriver. 
        # chromedrivermanager automatically installs and manages it for us.
        driver = webdriver.Chrome(service=service, options=chrome_options)
        ############################################################################
        return driver

class Page:
    '''This class represents a webpage as an object with the data we care about.'''
    
    def __init__(self, url):
        '''Simple constructor setting vlaues to the page.'''
        self.normalized_url = checker.normalize_url(url)
        self.aliases = []
        self.tracking_ids = []
        self.add_alias(url)
        self.error_code = ""
        self.load_time = 0
        self.date_crawled = datetime.now()
        self.cookies = []
        self.has_links = []
        self.has_external_links = []
        self.terms = 0
        self.title = ''
        self.is_file = 0

    def get_aliases(self):
        '''Return page aliases.'''
        return self.aliases

    def get_url(self):
        '''Return page url.'''
        return self.normalized_url

    def add_alias(self, alias):
        '''Add aditional aliases to the alias list.'''

        # Confirm alias is a new url.
        if alias not in self.aliases and alias.lower() != self.normalized_url:
            self.aliases.append(alias)

    def add_tracking_id(self, tracking_id, type):
        '''Add id and type to the tracking_id property of Page.'''

        # Create the dictionary.
        tracking_pair = {"id": tracking_id, "type": type}

        # Confirm the dictionary is new.
        if tracking_pair not in self.tracking_ids:
            self.tracking_ids.append(tracking_pair)

    def add_link(self, link):
        '''Add aditional links to the has_link list'''
        self.has_links.append(link)
    
    def add_external_link(self, link):
        '''Add aditional links to the has_external_link list'''
        self.has_external_links.append(link)

    def as_dict(self, config):
        '''Format Page information into a dictionary for easy storing.'''

        global pindex

        # Create empty "row dictionary".
        r_dict={}
        r_dict['scan_id']=scan_id+str(pindex)
        pindex+=1

        # Create "column dictionary" using Page attributes
        c_dict={
            "url": self.normalized_url,
            "aliases": self.aliases,
            "error_code": self.error_code,
            "tracking_ids": self.tracking_ids,
            "load_time": self.load_time,
            "date_crawled": self.date_crawled.strftime("%m/%d/%Y, %H:%M:%S"),
            "cookies": self.cookies,
            "links": self.has_links,
            "terms": self.terms,
            "title": self.title,
            "is_file": self.is_file
        }
        

        #Iterate through config file to know what columns are expected.
        for column in config['columns']:
            try:

                # Confirm if current column was checked in config window.
                if config['columns'][column]:
                    if column !='terms':

                        # Creates a row and gives it the value of that column.
                        r_dict.update([[column,c_dict[column]]])
                    else:
                        
                        # Confirm if terms file was provided in config window.
                        if(config['use_terms']):
                            r_dict.update([['terms',c_dict[column]]])
                        else:
                            r_dict.update([[config['term'],c_dict[column]]])
            except KeyError:
                pass
            except Exception as e:
                pass
        
        return r_dict

    def __str__(self):
        "Return the string version of the dicttionary."
        return str(self.self.as_dict())

class SpyTester(Tester):
    def __init__(self, config, date):
        super().__init__(config, date)
        self.counter_test = 0
        self.counter_start_driver = 0
        self.counter_identifier = 0
        self.counter_get_page_visited = 0
        self.counter_log_events = 0
        self.counter_page_loaded = 0
        self.counter_closed_driver = 0
        self.counter_driver_load = 0
        self.counter_check_standard = 0
        self.counter_page_created = 0
        self.counter_page_already_visited = 0
        self.counter_added_to_page_visited = 0
        self.counter_error_found = 0
        self.counter_cheked_errors = 0
        self.counter_page_fully_loaded = 0
        self.counter_crawled_page = 0
        self.counter_set_title = 0
        self.counter_set_cookies = 0
        self.counter_set_tracking_id = 0
        self.counter_finished_scrape = 0
        self.current_thread = threading.current_thread().getName()

    def add_identifier_to_url(self, url):
        self.counter_identifier += 1
        return super().add_identifier_to_url(url)
    
    def get_page_visited(self, url, pages_visited):
        self.counter_get_page_visited += 1
        return super().get_page_visited(url, pages_visited)
    def process_browser_logs_for_network_events(self, logs):
        self.counter_log_events += 1
        return super().process_browser_logs_for_network_events(logs)
    
    def page_loaded(self, driver):
        self.counter_page_loaded += 1
        return super().page_loaded(driver)

    def test_url(self, url, urls_to_visit, pages_visited):
        self.counter_test += 1
        return super().test_url(url, urls_to_visit, pages_visited)
    
    def count_driver_load(self):
        self.counter_driver_load += 1
    def count_check_standard(self):
        self.counter_check_standard += 1
    def count_page_created(self):
        self.counter_page_created += 1
    def count_page_already_visited(self):
        self.counter_page_already_visited += 1
    def count_pages_visited_add(self):
        self.counter_added_to_page_visited += 1
    def count_error_found(self):
        self.counter_error_found += 1
    def count_checked_errors(self):
        self.counter_cheked_errors += 1
    def count_page_fully_loaded(self):
        self.counter_page_fully_loaded += 1
    def count_crawled_page(self):
        self.counter_crawled_page += 1
    def count_set_title(self):
        self.counter_set_title += 1
    def count_set_cookies(self):
        self.counter_set_cookies += 1
    def count_set_tracking_ids(self):
        self.counter_set_tracking_id += 1
    def finished_scrape(self):
        self.counter_finished_scrape += 1

    # def start_driver(self):
    #     self.counter_start_driver += 1
    #     return super().start_driver(self)
        
    def __del__(self):
        print('report')

class Scraper():
    def __init__(self, config):
        self.urls_to_visit = set()
        self.pages_visited = []
        self.config = config
        self.max_pages = config['max']
        self.thread_size = config['threads']
        self.time_per_scrape = []
        self.program_start = datetime.now()
        self.program_end = None
        self.date = datetime.today().strftime("%m-%d-%y %H-%M-%S")
        self.count = 0
        self.testers = []

    def get_pages(self):
        '''Add first pages to the queue based on the configurations of the program.
            This method only runs at the start of the program.'''

        # Get URL's from the sitemap.
        if self.config['sitemap']:
            page = Page("https://www.byui.edu/sitemap")
            self.pages_visited.append(page)

            # Use a normal requests.get call here 
            # instead of accessing it through selenium.
            resp = requests.get("https://www.byui.edu/sitemap",
                                headers={'User-Agent': 'Mozilla/5.0'})
            
            # Check that sitemap loads properly.
            if (resp.status_code == 200):
                root = ElementTree.fromstring(resp.content)
                for child in root:
                    if child.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}url":
                        for url in child:
                            if url.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}loc":
                                page_url = checker.normalize_url(url.text)

                                # Perform standard validation check.
                                if (checker.check_standard(page_url)):
                                    page.add_link(page_url)
                                    page.is_file = 1
                                    self.urls_to_visit.add(page_url)
            else:

                # Attatch error code to page.
                page.error_code = resp.status_code

        # Get URLs from a txt file.
        if(self.config['use_links']):
            with open(self.config['links'], "r") as file:
                for line in file:
                    page_url = checker.normalize_url(line.strip())
                    self.urls_to_visit.add(page_url)

        if(self.config['catalog']):
            
            # Get the ID of the catalog from Kuali
            catalog_id = requests.get('https://byui.kuali.co/api/v1/catalog/public/catalogs/current').json()['_id']

            # Access Kuali to get the addresses for all the pages in the catalog.
            navigation = requests.get(f"https://byui.kuali.co/api/v1/catalog/public/catalogs/{catalog_id}").json()['settings']['catalog']['navigation']

            # Create a complete URL with the page address and add to queue.
            for page in navigation:
                self.urls_to_visit.add('https://www.byui.edu/catalog/#' + page['to'])

    def scrape_page(self, sublist):
        '''Function to scrape a single page.'''

        if self.count > self.max_pages:
            return
        
        if len(sublist) == 0:
            return 
        
        tester = SpyTester(self.config, self.date)
        self.testers.append(tester)
        for url in sublist:

            self.urls_to_visit.remove(url)

            try:
                page_scrape_start = datetime.now()
                self.count +=1
                tester.test_url(url, self.urls_to_visit, self.pages_visited)
                page_scrape_end = datetime.now()

                # Store scrape time per page
                self.time_per_scrape.append((page_scrape_end - page_scrape_start).total_seconds())
            except (Exception) as e:
                print('Error: ',e)
                print(traceback.print_exc())
        
        tester.driver.quit()

    def get_sublists(self, batch_urls):
        '''Create a list of lists with urls based on the size of threads.'''

        # Calculate the size of each sublist.
        sublist_size = (len(batch_urls) + self.thread_size - 1) // self.thread_size

        # Create a new list of lists.
        return [batch_urls[i * sublist_size:(i + 1) * sublist_size] for i in range(self.thread_size)]
        
    def main(self):
        ''' Run the entire program with multithreadng.'''
        # Don't let the computer sleep while the script runs. 
        # If the computer sleeps, the crawl breaks
        set_keepawake(keep_screen_awake=False)

        # Create initial list of pages to visit.
        self.get_pages()        
        
        # Continue until we have reached our limit or we run out of links in the set.
        while self.urls_to_visit and self.count < self.max_pages:

            # Pages till we have reached our limit.
            pages_left = self.max_pages - self.count
            print(f"\n \t Sites left until max: {pages_left} \n")

            # Check if we have more urls than our limit allows us to go through.
            if len(self.urls_to_visit) > pages_left:
                
                # Create a sublist of the # of urls we need to get to our limit.
                batch_urls = list(self.urls_to_visit)[0:pages_left]

            else: 
                batch_urls = list(self.urls_to_visit)

            # Create a new list of lists to give every thread their own list.
            sublists = self.get_sublists(batch_urls)

            print('\n\n \t Created a new executor \n')
            print('Sites left in list: ', len(self.urls_to_visit))

            if len(self.urls_to_visit) < 15:
                print('URLS to visit: ')
                for url in self.urls_to_visit:
                    print(url, '\n')


            with ThreadPoolExecutor(self.thread_size) as executor:
                executor.map(self.scrape_page, sublists)


            print('Scrape count: ', self.count)
            print('Pages visited: ', len(self.pages_visited))

            executor.shutdown(wait=False, cancel_futures=True)
            print('\n\n \t Killed executor \n\n')


        # Store data collected
        #self.finish()
       
    def finish(self):
        '''Save the crawl data into a csv file or json file.'''
        
        self.program_end = datetime.now()

        data = [page.as_dict(self.config) for page in self.pages_visited]
        
        templatejson ={self.date: data}

        # if not os.path.exists('results'):
        #     os.makedirs('results')

        # # For an easier interpreteation of data every new scan will be
        # # called the "recent_site_scan".
        original_filename = "recent_site_scan.json"
        
        # try:
        #     # Get the date of the most recent scan file and update it's name to 
        #     # "byuipages {date}" to keep a file naming standard.
        #     with open(original_filename, 'r') as f:
        #         prev_json = json.load(f)
        #         old_time_stamp = list(prev_json.keys())[0]
        #         new_filename = f'results/byuipages {old_time_stamp}.json'
            
        #     os.rename(original_filename, new_filename)
        # except FileNotFoundError:
        #     pass

        # Save as a JSON file.
        with open(original_filename, 'x') as f:
            json.dump(templatejson, f)

        print('\t GETTING STATS \n')

        avg = round(sum(self.time_per_scrape)/len(self.time_per_scrape), 2)
        max_time = max(self.time_per_scrape)
        total_time = round((self.program_end - self.program_start).total_seconds(), 2)
        with open('scraper_stats.txt', 'a') as stats:
            stats.write(f'\nDate: {self.date}, MULTITHREADING WITH CLASSES ATTEMPT, Average Time Per Page: {avg}, Max Time: {max_time}, Total time: {total_time/60} mins, Amount of pages visited: {len(self.pages_visited)}, Pages Requessted {self.max_pages}')

        print('total pages visited: ', len(self.pages_visited))
        print('total pages in urls_to_visit: ', len(self.urls_to_visit))
        unset_keepawake()
        print('\n Next step is os._exit ')
        sys.exit(0)
        #os._exit(0)

    def sighandle(self, sig, frame):
        '''Run the finish function if the program is closed early for some reason'''
        self.finish()


# This is mostly good practice, this runs the self.main function 
# only if we are in the main thread.
if __name__ == "__main__":
    '''Initial set up using confi.py and reading its output.'''
    #os.system('config.pyw')
    import config
    with open('config.json') as f:
        config = json.loads(f.read())
    
    scraper=Scraper(config)
    
    # Sets up the sighandle function so that it will capture exit signals.
    signal.signal(signal.SIGINT, scraper.sighandle)

    # Run the program.
    scraper.main()

