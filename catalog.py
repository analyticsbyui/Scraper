import requests
catalog_id=requests.get('https://byui.kuali.co/api/v1/catalog/public/catalogs/current').json()['_id']
print(catalog_id)
navigation=requests.get(f"https://byui.kuali.co/api/v1/catalog/public/catalogs/{catalog_id}").json()['settings']['catalog']['navigation']
urls=[]
for page in navigation:
    urls.append('https://www.byui.edu/catalog#'+page['to'])
