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
#import os
# config variables
crawl = True
use_sitemap = True
max_pages = 10
'''
aliases = True #The scraper will not be efficient without comparing aliases. Aliases modes maybe?
errorCode = True #Very few cases almost not used.
tracking_ids = True # this can save some time.
loadTime = True # Could not sev too much time.
dateCrawled = True
cookies =True
links = True #Almost same as Crawled
terms = True
'''




scan_id=datetime.now().strftime('%d%m%Y')
pindex=1

# add_identifier_to_url adds an identifier to the url for potential tracking purposes
def add_identifier_to_url(url):
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
    cases={'str':[],'re':[]}
    with open(path) as file:
        for line in file:
            line=line.replace('\n','')
            line=line.replace('\r','')
            if line[0]=='/':
                if line[-1]=='/':
                    cases['re'].append(line[1:-1])
                else:
                    cases['str'].append(line)
            else:
                cases['str'].append(line)
    return cases    

def check_matches(cases,text,not_reversed=True,callback=None):
        #print(blacklist)
    for q in cases['str']:
        if q in text:
            if callback!=None:
                callback(text)
            return not_reversed
    for q in cases['re']:
        if re.search(q,text)!=None:
            if callback!=None:
                callback(text)
            return not_reversed
    return not not_reversed

def check_matches_config(cases_name,text,not_reversed=True,callback=None):
    cases=globals()[cases_name]
    global config
    if (cases==None):
        cases=init_matches(config[cases_name])
    return check_matches(cases,text,not_reversed,callback)
def check_blacklist_callback(url):
    if(config['use_blacklist_output']):
        with open(config['blacklist_output'],'a') as f:
            print(url,file=f)
def check_blacklist(url):
    return check_matches_config('blacklist',url,False,callback=check_blacklist_callback)
whitelist=None
def check_whitelist(url):
    return check_matches_config('whitelist',url)
terms=None
def check_terms(body):
    return check_matches_config('terms',body.lower())
normalize_excuses=init_matches('normalize_exceptions.txt')
def check_normalize(url):
    global normalize_excuses
    return check_matches(normalize_excuses,url)
# normalize_url removes query string and hash and it makes sure we're using https
def normalize_url(url):
    if(check_normalize(url)):
        return url
    else:
        url = url.split("?")[0]
        url = url.split("#")[0]
        url = url.split("://")[1]

        if url[-1] == '/':
            url = url[:-1]

        return "https://" + url.lower()

# gets a page object from the pages_visited list
def get_page_visited(url):
    url = normalize_url(url)
    return next((page for page in pages_visited if page.get_url() == url or url in page.get_aliases()), None)

# process_browser_logs_for_network_events filters network requests from browser logs
def process_browser_logs_for_network_events(logs):
    for entry in logs:
        log = json.loads(entry["message"])["message"]
        if (
            "Network.response" in log["method"]
            or "Network.request" in log["method"]
            or "Network.webSocket" in log["method"]
        ):
            yield log


# Page represents a webpage as an object with the data we care about
class Page:
    def __init__(self, url):
        self.normalized_url = normalize_url(url)
        self.aliases = []
        self.tracking_ids = []
        self.add_alias(url)
        self.errorCode = ""
        self.loadTime = 0
        self.dateCrawled = datetime.now()
        self.cookies = []
        self.haslinks = []
        self.terms = 0
        self.title = ''
        self.is_file = 0

    def get_aliases(self):
        return self.aliases

    def get_url(self):
        return self.normalized_url

    def add_alias(self, alias):
        if alias not in self.aliases and alias.lower() != self.normalized_url:
            self.aliases.append(alias)

    def add_tracking_id(self, tracking_id, type):
        tracking_pair = {"id": tracking_id, "type": type}
        if tracking_pair not in self.tracking_ids:
            self.tracking_ids.append(tracking_pair)

    def add_link(self, link):
        self.haslinks.append(link)

    def as_dict(self):
        global pindex
        r_dict={}
        c_dict={
            "url": self.normalized_url,
            "aliases": self.aliases,
            "errorCode": self.errorCode,
            "tracking_ids": self.tracking_ids,
            "loadTime": self.loadTime,
            "dateCrawled": self.dateCrawled,
            "cookies": self.cookies,
            "links": self.haslinks,
            "terms": self.terms,
            "title": self.title,
            "is_file": self.is_file
        }
        global config
        for column in config['columns']:
            try:
                if config['columns'][column]:
                    if column !='terms':
                        r_dict.update([[column,c_dict[column]]])
                    else:
                        if(config['use_terms']):
                            r_dict.update([['terms',c_dict[column]]])
                        else:
                            r_dict.update([[config['term'],c_dict[column]]])
            except KeyError:
                pass
            except Exception as e:
                pass
        r_dict['scan_id']=scan_id+str(pindex)
        pindex+=1
        return r_dict

    def __str__(self):
        return str(self.as_dict())

# page_loaded checks the ready state of the web page
def page_loaded(driver):
    if(config['catalog']):
        return driver.execute_script("return document.readyState") == "complete" and driver.execute_script("return ((new Date()).getTime()-lastTime)>2000") #and  expected_conditions.presence_of_element_located((By.ID,'__KUALI_TLP'))
    else:
        return driver.execute_script("return document.readyState") == "complete" 

# test_url runs the main logic for crawling a webpage
def test_url(url):
    global config
    print(url)

    page_url_with_identifier = add_identifier_to_url(url)

    # load the page
    try:
        # reset cookies after every page so they're fresh
        driver.delete_all_cookies()
        driver.get(page_url_with_identifier)
        #driver.refresh()
    except (MaxRetryError, ConnectionResetError) as e:
        #finish()
        return
    except (Exception) as e:
        # this should ideally never happen
        print("super broken", e)
        return

    current_url = normalize_url(driver.current_url)

    page = Page(current_url)

    # handle redirects
    if current_url != url:
        # a mismatching url after the page loads probably means we were redirected
        print("url mismatch. redirected?")

        if current_url in urls_to_visit:
            urls_to_visit.remove(current_url)

        page_visited = get_page_visited(current_url)

        if page_visited != None:
            page_visited.add_alias(url)
            print("already visited")
            return
        else:
            page.add_alias(url)

    pages_visited.append(page)

    # search for chrome error
    try:
        elem = driver.find_element(By.ID, "error-information-popup-content")

        print(elem.find_element(By.CLASS_NAME, "error-code").text)
        page.errorCode = elem.find_element(By.CLASS_NAME, "error-code").text
        return
    except:
        pass

    # chrome returns empty page source if page is not found while running headless
    if "<body></body>" in driver.page_source:
        print("body empty")
        page.errorCode = "404"
        #return

    # check page title for 404
    if "404" in driver.title:
        print("404")
        page.errorCode = "404"
        #return

    # crawl the page for links
    # because the page load is set to eager, we need to wait until everything else is loaded before checking network requests and cookies
    driver.execute_script("lastTime=(new Date()).getTime() ; const config = { attributes: true, childList: true, subtree: true };const targetNode = document.body;const callback = (mutationList, observer) => {lastTime=(new Date()).getTime();};const observer = new MutationObserver(callback);observer.observe(targetNode, config);")
    WebDriverWait(driver, timeout=10).until(page_loaded)
    #driver.save_screenshot(str(len(pages_visited))+'.png')
    
    if crawl:
        #if(config['catalog']):
        #    sleep(1)
        links = driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            try:
                url = link.get_attribute("href")
                if url == None:
                    continue

                if "://" not in url:
                    continue

                if url.strip() == "":
                    continue

                normalized_url = normalize_url(url)

                page.add_link(url)

                # check if the url contains scope domain and that it isn't already queued to be visited
                if "byui.edu" in normalized_url and normalized_url not in urls_to_visit and get_page_visited(url)== None and (not config['use_blacklist'] or check_blacklist(url))  and (not config['use_whitelist'] or check_whitelist(url)):
                    # check file extensions
                    if not any(substring in normalized_url for substring in [".pdf", ".pptx", ".ppt", ".doc", ".docx", ".xlsx", ".xls", ".xlsm", ".exe", ".zip", ".jpg", ".png", ".mp3", ".mp4"]):
                        urls_to_visit.append(normalized_url)
                    elif config['files']:
                        page=Page("normalized_url")
                        pages_visited.append(page)
            except StaleElementReferenceException:
                pass

    
    

    page.cookies = [cookie['name'] for cookie in driver.get_cookies()]

    if(config['columns']['tracking_ids']):

        logs = driver.get_log("performance")
        events = process_browser_logs_for_network_events(logs)

        # find analytics collect calls
        for event in events:
            if event['method'] == 'Network.requestWillBeSent':
                url = event['params']['request']['url']
                docUrl = event['params']['documentURL']
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)

                # if the url the request was made for doesn't match the page we're scanning, skip it
                if docUrl != driver.current_url:
                    continue

                if "google-analytics.com/collect" in url or "google-analytics.com/j/collect" in url:
                    page.add_tracking_id(query_params['tid'][0], "GA")

                if "googletagmanager.com/gtm.js" in url:
                    page.add_tracking_id(query_params['id'][0], "GTM")

                if "googletagmanager.com/gtag/js" in url:
                    page.add_tracking_id(query_params['id'][0], "GTAG")

    # this load time isn't used for anything, i just threw it in at some point.
    # it's worth double checking at some point
    # this SO answer gives a good overview of what checkpoints are logged in the page loading https://stackoverflow.com/a/14878493
    if(config['columns']['terms'] and not config['use_terms']):
        body=driver.execute_script('return document.body.innerText')
        page.terms=(config['term'] in body)+0
    elif config['use_terms']:
        body=driver.execute_script('return document.body.innerText')
        page.terms=(check_terms(body))+0
    if(config['columns']['loadTime']):
        page.loadTime = driver.execute_script(
        "return window.performance.timing.domContentLoadedEventEnd - window.performance.timing.navigationStart")
    if(config['columns']['title']):
        page.title = driver.title

def start_driver():
    global driver
    global config
    # this block sets up selenium settings
    ################################################################################
    chrome_options = Options()
    # these settings are an effort to disable file downloads
    prefs = {
        "download_restrictions": 3,
        "download.open_pdf_in_system_reader": False,
        "download.prompt_for_download": True,
        "download.default_directory": "/dev/null",
        "plugins.always_open_pdf_externally": False
    }
    chrome_options.add_experimental_option(
        "prefs", prefs
    )

    # default capabilities
    #capabilities = DesiredCapabilities.CHROME
    chrome_options.capabilities.update(DesiredCapabilities.CHROME)

    # enable logging so we can get the network logs
    chrome_options.set_capability("goog:loggingPrefs", {'performance': 'ALL'})

    # Turn off gpu and extensions, these can cause weird problems
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    # run headless so that the chrome window stays hidden
    chrome_options.add_argument("--enable-javascript")
    if(not config['catalog']):
        
        chrome_options.add_argument("--headless")

    # eager loading lets the program continue after the html is loaded, but before everthing else has finished loading
    # we use this so we can crawl the page for links before continuing on to log analytics calls
    chrome_options.page_load_strategy = "eager"

    service = Service(executable_path=ChromeDriverManager().install())

    # set up the webdriver. chromedrivermanager automatically installs and manages it for us
    driver = webdriver.Chrome(service=service, options=chrome_options)
    ################################################################################

def get_pages():
    global urls_to_visit
    global use_sitemap
    global config
    # get initial page list from the sitemap
    # we use a normal requests.get call here instead of accessing it through selenium
    if use_sitemap:
        page = Page("https://www.byui.edu/sitemap")
        pages_visited.append(page)
        resp = requests.get("https://www.byui.edu/sitemap",
                            headers={'User-Agent': 'Mozilla/5.0'})
        if (resp.status_code == 200):
            root = ElementTree.fromstring(resp.content)
            for child in root:
                if child.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}url":
                    for url in child:
                        if url.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}loc":
                            page_url = normalize_url(url.text)

                            if "byui.edu" in page_url  and (not config['use_blacklist'] or check_blacklist(page_url)) and (not config['use_whitelist'] or check_whitelist(page_url) ):
                                page.add_link(page_url)
                                page.is_file=1
                                urls_to_visit.append(page_url)
    if(config['use_links']):
        # this code below will load in URLs from a txt file
        with open(config['links'], "r") as file:
           for line in file:
               page_url = normalize_url(line.strip())
               urls_to_visit.append(page_url)
    if(config['catalog']):
        catalog_id=requests.get('https://byui.kuali.co/api/v1/catalog/public/catalogs/current').json()['_id']
        navigation=requests.get(f"https://byui.kuali.co/api/v1/catalog/public/catalogs/{catalog_id}").json()['settings']['catalog']['navigation']
        urls=[]
        for page in navigation:
            urls_to_visit.append('https://www.byui.edu/catalog#'+page['to'])

# main sets up selenium, checks the sitemap for the initial list of pages, and runs the crawl
def main():
    # don't let the computer sleep while the script runs. if the computer sleeps, the crawl breaks
    set_keepawake(keep_screen_awake=False)
    global driver
    global urls_to_visit
    global pages_visited

    urls_to_visit = []
    pages_visited = []

    start_driver()

    get_pages()

    # crawl each page in the list
    count = 0
    while len(urls_to_visit) > 0 and count < max_pages:
        url = urls_to_visit.pop()
        count += 1
        try:
            test_url(url)
        except (Exception) as e:
            print('Error: ',e)
            traceback.print_exc()
#            test_url(url)

        print("Sites left: " + str(len(urls_to_visit)),
              "Visited: " + str(count))
              
    finish()

# finish saves the crawl data into a csv file
def finish():
    with open('config.json') as f:
        config=json.loads(f.read())
    df = pd.DataFrame.from_records([page.as_dict() for page in pages_visited])
    date = datetime.today().strftime("%m-%d-%y %H-%M-%S")
    df.to_csv(f"byuipages {date}.csv")

    driver.quit()
    unset_keepawake()
    sys.exit(0)

# run the finish function if the program is closed early for some reason
def sighandle(sig, frame):
    finish()
config=None 
# this is mostly just good practice, but this runs the main function only if we are in the main thread
if __name__ == "__main__":
    # this sets up the sighandle function so that it will capture exit signals
    #os.system('config.pyw')
    import config
    with open('config.json') as f:
        config=json.loads(f.read())
    max_pages = config['max']
    crawl = config['crawl']
    use_sitemap = config['sitemap']
    signal.signal(signal.SIGINT, sighandle)
    main()
