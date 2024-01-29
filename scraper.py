from datetime import datetime
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import requests
from xml.etree import ElementTree
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
import json
from urllib.parse import urlparse
from urllib.parse import parse_qs
import signal
import sys
import pandas as pd
from webdriver_manager.chrome import ChromeDriverManager
from urllib3.exceptions import MaxRetryError
from wakepy import set_keepawake, unset_keepawake
import re
import traceback
import os
# config variables
max_pages = 10
'''
aliases = True #The scraper will not be efficient without comparing aliases. Aliases modes maybe?
error_code = True #Very few cases almost not used.
tracking_ids = True # this can save some time.
load_time = True # Could not sev too much time.
date_crawled = True
cookies =True
links = True #Almost same as Crawled
terms = True
'''




scan_id=datetime.now().strftime('%d%m%Y')
pindex=1

def add_identifier_to_url(url):
    ''' Adds an identifier to the url for potential tracking purposes.
        Returns a string.'''

    # Check for query string.
    if "?" in url:
        return url + "&analyticsIntegrationVerificationBot"
    else:
        return url + "?analyticsIntegrationVerificationBot"
    
blacklist=None
def check_blacklist_old(url):
    global blacklist
    global config
    #print(config['blacklist'])
    if (blacklist==None):
        blacklist={'str':[],'re':[]}
        with open(config['blacklist']) as file:
            #print('m')
            for line in file:
                #print('a',line)
                line=line.replace('\n','')
                line=line.replace('\r','')
                if line[0]=='/':
                    if line[-1]=='/':
                        #blacklist['re'].append(re.compile(line))
                        #print('compile')
                        blacklist['re'].append(line[1:-1])
                    else:
                        #Warning for know just added it
                        blacklist['str'].append(line)
                else:
                    blacklist['str'].append(line)
        print(blacklist)
    for q in blacklist['str']:
        if q in url:
            if(config['use_blacklist_output']):
                with open(config['blacklist_output'],'a') as f:
                    print(url,file=f)
            return False
    for q in blacklist['re']:
        if re.search(q,url)!=None:
            if(config['use_blacklist_output']):
                with open(config['blacklist_output'],'a') as f:
                    print(url,file=f)
            return False
    return True


def init_matches(path):
    ''' Opens a file and creates cases for a string search or 
        regex comparison.
        Returns a dictionary '''
    
    # Create dictionary.
    cases={'str':[],'re':[]}

    # Open file.
    with open(path) as file:
        for line in file:

            # Format line ignoring spaces.
            line=line.replace('\n','')
            line=line.replace('\r','')
            
            # Check if line is regex format.
            if line[0]=='/':
                if line[-1]=='/':
                    
                    # Append to regex key.
                    cases['re'].append(line[1:-1])
                else:

                    # Append to string key.
                    cases['str'].append(line)
            else:

                # Append to string key.
                cases['str'].append(line)

    return cases    

def check_matches(cases,text,callback=None):
    ''' Check for matches between a set of cases and a given text.
        Callback is only passed when this function is originally called
        by check_blacklist
        Returns a bool.'''
        
    found = True
    for q in cases['str']:
        
        # Search for word in provided text.
        if q in text:

            # If callback is passed, call the function.
            if callback!=None:
                callback(text)

            # Word found.
            return found
    
    for q in cases['re']:
        
        # Perform a regex match.
        if re.search(q,text)!=None:

            # If callback is passed, call the function.
            if callback!=None:
                callback(text)

            # Match found.
            return found
    
    # Text does not have a match.
    return not found

def check_matches_config(cases_name,text,callback=None):
    '''Wrapper Function:
        This function is made to call check_matches with the right params based 
        on the caller of this function (e.g. whitelist or blacklist .
        Returns a bool.'''
    
    # This line was used to get the cases from global variables, it would involve setting
    # the variable somwhere in the code, we do it all through the config window now.
    cases=globals()[cases_name]
    
    global config

    # Check if variables exist or if they are empty
    if (cases==None):

        # Call function to create cases.
        cases=init_matches(config[cases_name])
  
    # Call main check function, return its result.
    return check_matches(cases,text,callback)

def check_blacklist_callback(url):
    ''' A callback function that will write the given url to the 
        blacklist_output file'''
    
    # Check that there is a file specifided in the configuration.
    if(config['use_blacklist_output']):

        with open(config['blacklist_output'],'a') as f:
            
            # Write a line with the given url
            print(url,file=f)

def check_blacklist(url):
    '''Cheks if the given url is valid by checking the blacklist.
        Returns a bool.'''
    
    # Call the wrapper function
    if check_matches_config('blacklist',url,callback=check_blacklist_callback):

        # If url is blacklisted then it is not valid, return False
        return False
    else:

        # If url is not blacklisted then it is valid, return True
        return True

#whitelist=None
def check_whitelist(url):
    '''Checks if the given url is valid by checking the whitelist.
        Returns a bool.'''
    
    # Call the wrapper function.
    return check_matches_config('whitelist',url)

def check_standard(url):
    '''Checks if url is in scope domain, is not in blacklist or is 
        in included in whitelist.
        Returns a bool.'''
    
    return ('byui.edu' in url
            and (not config['use_blacklist'] or check_blacklist(url))  
            and (not config['use_whitelist'] or check_whitelist(url)))

#terms=None
def check_terms(body):
    '''Checks if the given content of a page includes any terms given in the
        config settings.
        Returns a bool.'''
    
    # Call the wrapper function
    return check_matches_config('terms',body.lower())

# Create cases from the normalize file.
normalize_excuses = init_matches('normalize_exceptions.txt')

def check_normalize(url):
    '''Checks if the given url has the standard structure for a byui url page.
        Returns a bool.'''
    
    # Access the already created excuses.
    global normalize_excuses

    # Call main check function, return its result.
    return check_matches(normalize_excuses,url)

def normalize_url(url):
    ''' Removes query string and hash and makes sure we're using https.
        Returns a string.'''
    
    # Check if we need to format the url or it is already done.
    if(check_normalize(url)):
        return url
    else:
        url = url.split("?")[0]
        url = url.split("#")[0]
        url = url.split("://")[1]

        # Remove slash from the end of the url.
        if url[-1] == '/':
            url = url[:-1]

        # Return formated url.
        return "https://" + url.lower()

tag = r"(\?|\&)analyticsIntegrationVerificationBot"

def check_identifier(url):
    '''Look for identifier and replace.'''
    
    # Replace our identifier if it exists in the link.
    if re.search(tag, url) != None:
        url = re.sub(tag, "", url)

    return url

def get_page_visited(url):
    ''' Gets a Page object from the pages_visited list.
        Returns a Page.'''
    
    url = normalize_url(url) #this might not be necessary if we normalize its inputs before calling the function

    # Get the first page that matches the provided url or has the url as alias.
    # If not found return None.
    return next((page for page in pages_visited if page.get_url() == url or url in page.get_aliases()), None)

def process_browser_logs_for_network_events(logs):
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


class Page:
    '''This class represents a webpage as an object with the data we care about.'''
    
    def __init__(self, url):
        '''Simple constructor setting vlaues to the page.'''
        self.normalized_url = normalize_url(url)
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

    def as_dict(self):
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
        global config

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
        return str(self.as_dict())

def page_loaded(driver):
    '''Checks the ready state of the web page.
        Returns a bool.'''

    if(config['catalog']):
        
        # Confirm that document has loaded and that last update happened more 
        # than 2 seconds ago. 
        return (driver.execute_script("return document.readyState") == "complete" 
                and driver.execute_script("return ((new Date()).getTime()-lastTime)>2000")) #and  expected_conditions.presence_of_element_located((By.ID,'__KUALI_TLP'))
    else:

        # Confirm that document has loaded.
        return driver.execute_script("return document.readyState") == "complete" 

def test_url(url):
    '''Main logic for crawling a webpage.'''

    global config
    print(url)

    # Add identifier for potential analytic purposes.
    page_url_with_identifier = add_identifier_to_url(url)

    # Load the page.
    try:
        # Reset cookies after every page so they're fresh.
        driver.delete_all_cookies()
        driver.get(page_url_with_identifier)
    except (MaxRetryError, ConnectionResetError) as e:
        return
    except (Exception) as e:

        # This should ideally never happen.
        print("super broken", e)
        return

    current_url = driver.current_url
    
    # Check if current_url has scope domain and is not
    # in the blacklist.
    if not check_standard(current_url):
        return
    
    # Fromat current url to standard.
    current_url = normalize_url(driver.current_url)

    current_url = check_identifier(current_url)

    # Create a Page object
    page = Page(current_url)

    # Handle redirects.
    if current_url != url:
        
        # A mismatching url when page loads probably means we were redirected.
        print("url mismatch. redirected?")

        # Check if current_url is in queue to visit.
        if current_url in urls_to_visit:
            urls_to_visit.remove(current_url)

        # Check if page has already been visited.
        page_visited = get_page_visited(current_url)

        # Page has been visited, no need to continue scraping.
        if page_visited != None:

            # Set page's url as alias for visited page.
            page_visited.add_alias(url)
            print("Page Already visited")
            return
        else:

            # Add url as alias for the current Page object.
            page.add_alias(url)

    pages_visited.append(page)

    print(f'\n \tCurrent page visited count {len(pages_visited)}')

    # Search for chrome error in Single Page Applications.
    try:
        elem = driver.find_element(By.ID, "error-information-popup-content")
        print(elem.find_element(By.CLASS_NAME, "error-code").text)
        page.error_code = elem.find_element(By.CLASS_NAME, "error-code").text

        # Error found. No need to continue.
        return
    except:
        pass

    # Chrome returns empty page source if page is not found 
    # while running headless.
    if "<body></body>" in driver.page_source:
        print("body empty")
        page.error_code = "404"
        #return

    # Check page title for 404.
    if "404" in driver.title:
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



    # Crawl the page for links.
    # Since page load is set to eager, we need to wait until everything else is 
    # loaded before checking network requests and cookies.
    driver.execute_script('''
        lastTime=(new Date()).getTime();
        const config = { attributes: true, childList: true, subtree: true };
        const targetNode = document.body;
        const callback = (mutationList, observer) => {lastTime=(new Date()).getTime();};
        const observer = new MutationObserver(callback);observer.observe(targetNode, config);
                            ''')
    WebDriverWait(driver, timeout=30).until(page_loaded)
    # #driver.save_screenshot(str(len(pages_visited))+'.png')
    
    if config['crawl']:

        # Get all a tags.
        links = driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            try:
                link_url = link.get_attribute("href")
                
                # Replace our identifier if it exists in the link.
                link_url = check_identifier(link_url)

                # "href" not found.
                if link_url == None:
                    continue

                # Not an absolute link 
                if "://" not in link_url:
                    continue

                # Empty string
                if link_url.strip() == "":
                    continue

                normalized_url = normalize_url(link_url)
                if ("byui.edu" not in normalized_url and config["columns"]['external_links']):
                    page.add_external_link(link_url)
                elif "byui.edu" in normalized_url:
                    page.add_link(link_url)

                # Confirm url is not in queue to visit or already visited
                # and perform standard validation check.
                if (normalized_url not in urls_to_visit 
                    and get_page_visited(link_url)== None 
                    and check_standard(link_url)):
                    
                    # Check for file extensions.
                    if not any(substring in normalized_url for substring in 
                            [".pdf", ".pptx", ".ppt", ".doc", ".docx", ".xlsx", 
                            ".xls", ".xlsm", ".exe", ".zip", ".jpg", ".png", ".mp3", ".mp4"]):
                        
                        urls_to_visit.append(normalized_url)
                    elif config['files']:
                        '''
                            CHECK WITH JOSUE TO SEE WHAT IS EXPECTED WHEN  "FILES" IS SELECTED
                        '''
                        pages_visited.append(Page(normalized_url))
            except StaleElementReferenceException:
                pass

    
    if config["columns"]["title"]:
        page.title = driver.title
    
    # Set Page cookies from driver cookies.
    if config['columns']['cookies']:
        page.cookies = [cookie['name'] for cookie in driver.get_cookies()]

    # Check if tracking_ids was selected
    if config['columns']['tracking_ids']:

        logs = driver.get_log("performance")
        events = process_browser_logs_for_network_events(logs)

        # find analytics collect calls
        for event in events:
            if event['method'] == 'Network.requestWillBeSent':
                url = event['params']['request']['url']
                doc_url = event['params']['documentURL']
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)

                # If the url the request was made for doesn't match the page 
                # we're scanning, skip it.
                if doc_url != driver.current_url:
                    continue
                
                # Add tracking id's to Page object.
                if "google-analytics.com/collect" in url or "google-analytics.com/j/collect" in url:
                    page.add_tracking_id(query_params['tid'][0], "GA")

                if "googletagmanager.com/gtm.js" in url:
                    page.add_tracking_id(query_params['id'][0], "GTM")

                if "googletagmanager.com/gtag/js" in url:
                    page.add_tracking_id(query_params['id'][0], "GTAG")

    if config['columns']['terms'] and not config['use_terms']:

        # Search if term exists in page content.
        body = driver.execute_script('return document.body.innerText')
        page.terms = (config['term'] in body)+0
    elif config['use_terms']:
        body = driver.execute_script('return document.body.innerText')

        # Use check_matches to find if any term in file matches page content.
        page.terms = (check_terms(body))+0


    # Get the Load time of the current page with this script
    if config['columns']['load_time']:
        page.load_time = driver.execute_script(
        '''var entries = window.performance.getEntriesByType("navigation");
            if (entries.length > 0) {
                var navTiming = entries[0];
                var pageLoadTime = navTiming.loadEventEnd - navTiming.startTime;
                return Math.round((pageLoadTime / 1000) * 100) / 100;
                }''')

def start_driver():
    ''' Set up configurations for the selenium driver.'''
    global driver
    global config

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
    # if(not config['catalog']):
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

def get_pages():
    '''Add first pages to the queue based on the configurations of the program.
        This method only runs at the start of the program.'''
    global urls_to_visit
    global config

    # Get URL's from the sitemap.
    if config['sitemap']:
        page = Page("https://www.byui.edu/sitemap")
        pages_visited.append(page)

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
                            page_url = normalize_url(url.text)

                            # Perform standard validation check.
                            if (check_standard(page_url)):
                                page.add_link(page_url)
                                page.is_file = 1
                                urls_to_visit.append(page_url)
        else:

            # Attatch error code to page.
            page.error_code = resp.status_code

    # Get URLs from a txt file.
    if(config['use_links']):
        with open(config['links'], "r") as file:
           for line in file:
               page_url = normalize_url(line.strip())
               urls_to_visit.append(page_url)

    if(config['catalog']):
        
        # Get the ID of the catalog from Kuali
        catalog_id = requests.get('https://byui.kuali.co/api/v1/catalog/public/catalogs/current').json()['_id']

        # Access Kuali to get the addresses for all the pages in the catalog.
        navigation = requests.get(f"https://byui.kuali.co/api/v1/catalog/public/catalogs/{catalog_id}").json()['settings']['catalog']['navigation']

        # Create a complete URL with the page address and add to queue.
        for page in navigation:
            urls_to_visit.append('https://www.byui.edu/catalog/#' + page['to'])

def main():
    ''' Run the entire program in order'''
   
    # This is placed to keep track of how long it took to scrape everythin 
    # and the total scraping time.
    global time_per_scrape
    global program_start
    program_start = datetime.now()
    time_per_scrape = []

    # Don't let the computer sleep while the script runs. 
    # If the computer sleeps, the crawl breaks
    set_keepawake(keep_screen_awake=False)
    global driver
    global urls_to_visit
    global pages_visited

    urls_to_visit = []
    pages_visited = []


    # Set up Selenium Driver.
    start_driver()

    # Create initial list of pages to visit.
    get_pages()

    # Crawl each page in the list
    count = 0
    while len(urls_to_visit) > 0 and count < max_pages:
        url = urls_to_visit.pop()
        count += 1
        try:
            page_scrape_start = datetime.now()
            test_url(url)
            page_scrape_end = datetime.now()

            # Store scrape time per page
            # time_per_scrape[url] = (page_scrape_end - page_scrape_start).total_seconds()
            time_per_scrape.append((page_scrape_end - page_scrape_start).total_seconds())
        except (Exception) as e:
            print('Error: ',e)
            traceback.print_exc()

        print("Sites left: " + str(len(urls_to_visit)),
              "Visited: " + str(count))

    # Store data collected          
    #finish()
    
def finish():
    '''Save the crawl data into a csv file or json file.'''
    
    program_end = datetime.now()

    date = datetime.today().strftime("%m-%d-%y %H-%M-%S")

    # Save as a CSV file.
    # df = pd.DataFrame.from_records([page.as_dict() for page in pages_visited])
    # df.to_csv(f"byuipages {date}.csv")

    data = [page.as_dict() for page in pages_visited]
    
    templatejson ={date: data}

    # For an easier interpreteation of data every new scan will be
    # called the "recent_site_scan".
    original_filename = "recent_site_scan.json"
    
    try:
        # Get the date of the most recent scan file and update it's name to 
        # "byuipages {date}" to keep a file naming standard.
        with open(original_filename, 'r') as f:
            prev_json = json.load(f)
            old_time_stamp = list(prev_json.keys())[0]
            new_filename = f'byuipages {old_time_stamp}.json'
        
        os.rename(original_filename, new_filename)
    except FileNotFoundError:
        pass

    # Save as a JSON file.
    with open(original_filename, 'x') as f:
        json.dump(templatejson, f)

    avg = round(sum(time_per_scrape)/len(time_per_scrape), 2)
    max_time = max(time_per_scrape)
    total_time = round((program_end - program_start).total_seconds(), 2)
    with open('scraper_stats.txt', 'a') as stats:
        stats.write(f'\nDate: {date}, Average Time Per Page: {avg}, Max Time: {max_time}, Total time: {total_time}, Total amount of pages: {max_pages}')

    driver.quit()
    unset_keepawake()
    sys.exit(0)

def sighandle(sig, frame):
    '''Run the finish function if the program is closed early for some reason'''
    finish()

config = None

# This is mostly good practice, this runs the main function 
# only if we are in the main thread.
if __name__ == "__main__":
    '''Initial set up using confi.py and reading its output.'''
    #os.system('config.pyw')
    import config
    with open('config.json') as f:
        config = json.loads(f.read())
    max_pages = config['max']
    
    # Sets up the sighandle function so that it will capture exit signals.
    signal.signal(signal.SIGINT, sighandle)

    # Run the program.
    main()
