import os
import json 

current_location = os.path.dirname(os.path.realpath(__file__))

with open('config.json', 'r+') as f:
    data = json.loads(f.read())
    print('\n \n \n' + data["blacklist"] +'\n \n \n')

    if current_location not in data["blacklist"]: 
        data["blacklist"] = current_location + '/blacklist.txt'
    
    if current_location not in data["blacklist_output"]:
        data["blacklist_output"] = " "
    
    if current_location not in data["whitelist"]:
        data["whitelist"] = current_location + '/whitelist.txt'

    if current_location not in data["links"]:
        data["links"] = current_location + '/links.txt'


    f.seek(0)        # <--- should reset file position to the beginning.
    json.dump(data, f, indent=4)
    f.truncate()     # remove remaining part


    
