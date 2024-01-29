import re
import json

with open('config.json') as f:
        config = json.loads(f.read())

def init_matches(path):
    ''' Opens a file and creates cases for a string search or 
    regex comparison.
    Returns a dictionary '''
    
    # Create dictionary.
    cases = {'str':[],'re':[]}

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

# Create cases from the normalize file.
normalize_excuses = init_matches('normalize_exceptions.txt')

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
        on the caller of this function (e.g. whitelist or blacklist checker).
        Returns a bool.'''
    
    # Call function to create cases.
    cases= init_matches(config[cases_name])

    # Call main check function, return its result.
    return check_matches(cases,text,callback)

def check_blacklist_callback(url):
    ''' A callback function that will write the given url to the 
        blacklist_output file'''
    
    # Check that there is a file specifided in the configuration.
    if(config['use_blacklist_output']):

        with open(config['blacklist_output'],'a') as f:
            
            # Write a line with the given url
            print(url, file=f)

def check_blacklist(url):
    '''Cheks if the given url is valid by checking the blacklist.
        Returns a bool.'''
    
    # Call the wrapper function
    if check_matches_config('blacklist', url, callback = check_blacklist_callback):

        # If url is blacklisted then it is not valid, return False
        return False
    else:

        # If url is not blacklisted then it is valid, return True
        return True

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

def check_terms(body):
    '''Checks if the given content of a page includes any terms given in the
        config settings.
        Returns a bool.'''
    
    # Call the wrapper function
    return check_matches_config('terms', body.lower())   

def check_normalize( url):
    '''Checks if the given url has the standard structure for a byui url page.
        Returns a bool.'''

    # Call main check function, return its result.
    return check_matches(normalize_excuses, url)

def normalize_url( url):
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
