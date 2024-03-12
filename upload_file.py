import os
import requests


def add_context(main_url, site_url, headers, cookies):
    
    # Make the request
    response = requests.post(f'{main_url}{site_url}/_api/contextinfo', headers=headers, cookies=cookies)

    # Add necessary headers for upload
    headers['X-RequestDigest']=response.json()['d']['GetContextWebInformation']['FormDigestValue']


def upload_small_file(main_url, site_url, folder_url, file_path, headers, cookies):
    '''File Smaller than 200 mb can be sent in one request'''
    # # Endpoint to upload file
    upload_url = f"{main_url}{site_url}/_api/web/getfolderbyserverrelativeurl('{folder_url}')/Files/add(url='{file_path.split('/')[-1]}',overwrite=true)"

    # Read the file content
    with open(file_path, 'rb') as file:
        file_content = file.read()



    headers['Content-Type']= 'application/octet-stream'

    # Send the file to SharePoint
    response = requests.post(upload_url, data=file_content, headers=headers, cookies=cookies)

    # Check the response
    if response.status_code == 200:
        print(f"Successfully request. \n")
    else:
        print("Error in request: \n\t")
        print(response)



def create_upload_session(main_url, site_url, folder_url, file_name, headers, cookies):
    '''Function to start upload session'''
    
    # Get the FormDigestValue from the context
    response1 = requests.post(f"{main_url}{site_url}/_api/contextinfo",cookies=cookies, headers=headers)

    # Add necessary headers for upload
    headers['X-RequestDigest']=response1.json()['d']['GetContextWebInformation']['FormDigestValue']

    url = f"{main_url}{site_url}/_api/web/getfolderbyserverrelativeurl('{folder_url}')/Files/add(url='{file_name}',overwrite=true)"
    
    response = requests.post(url, headers=headers,cookies=cookies)
    if response.status_code == 200:
        data = response.json()
        return data['d']['UniqueId']
    else:
        raise Exception("There was an issue creating the Upload Session")


def start_upload(main_url, site_url, folder_url, file_name, session_id,file_content,  headers, cookies):
    
    #a1 = f"%27%2F{site_url}%2F{folder_url}%27"
    a1 = f"%27%2F{site_url}%2F{folder_url}%2F{file_name}%27"
    a2 = f"%27{file_name}%27"
    a3 = f"guid%27{session_id}%27"
    #upload_url = f"{main_url}{site_url}/_api/web/GetFolderByServerRelativePath(DecodedUrl=@a1)/Files/AddStubUsingPath(DecodedUrl=@a2)/StartUploadFile(uploadId=@a3)?@a1={a1}&@a2={a2}&@a3={a3}"
    #upload_url = f"{main_url}{site_url}/_api/web/GetFolderByServerRelativePath(DecodedUrl=@a1)/Files/AddStubUsingPath(DecodedUrl=@a2)?@a1={a1}&@a2={a2}"
    upload_url = f"{main_url}{site_url}/_api/web/GetFileByServerRelativePath(DecodedUrl=@a1)/StartUploadFile(uploadId=@a3)?@a1={a1}&@a2={a2}&@a3={a3}"
    
    response = requests.post(upload_url, data=file_content, cookies=cookies, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"There was an issue starting the upload, status: {response.status_code}")

def upload_chunk(main_url, site_url, file_name, folder_url, upload_id, file_content, offset, headers, cookies):
    '''Function to upload a chunk'''
    a1 = f"%27%2F{site_url}%2F{folder_url}%2F{file_name}%27"
    a2 = upload_id
    a3 = offset

    url = f"{main_url}{site_url}/_api/web/GetFileByServerRelativePath(DecodedUrl=@a1)/ContinueUpload(uploadId=@a2,fileOffset=@a3)?@a1={a1}&@a2=guid%27{a2}%27&@a3={a3}"
    
    response = requests.post(url, data=file_content,cookies=cookies, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f'There was an issue continuing the upload at offset: {offset}, status: {response.status_code} \n {response.text}')   

def finish_upload(main_url, site_url, file_name, folder_url, upload_id, file_content, offset, headers, cookies ):
    '''Function to finish the upload'''

    a1 = f"%27%2F{site_url}%2F{folder_url}%2F{file_name}%27"
    a2 = upload_id
    a3 = offset

    url = f"{main_url}{site_url}/_api/web/GetFileByServerRelativePath(DecodedUrl=@a1)/FinishUpload(uploadId=@a2,fileOffset=@a3)?@a1={a1}&@a2=guid%27{a2}%27&@a3={a3}"
    response = requests.post(url, data=file_content, headers=headers,cookies=cookies)
    if response.status_code != 200:
        raise Exception(f'There was an issue finishing the upload at offset: {offset}, status: {response.status_code} \n {response.text}')

def chunked_upload(main_url, file_path, site_url, folder_url, headers, cookies):
    '''Main function to perform chunked upload'''

    # Define chunk size (10 MB)
    chunk_size = 10 * 1024 * 1024  # 10 MB

    # Get file name
    file_name = os.path.basename(file_path)

    # Start upload session
    upload_id = create_upload_session(main_url, site_url, folder_url, file_name)

    # Open the file
    with open(file_path, 'rb') as file:
        # Get file size
        file_length = os.path.getsize(file_path)
        offset = 0
        chunk = file.read(chunk_size)
        offset += chunk_size
        try:
            start_upload(main_url, site_url, folder_url, file_name, upload_id, chunk,  headers, cookies)
            # Upload chunks
            while offset+2*chunk_size-1  < file_length:#
                chunk = file.read(chunk_size)
                upload_chunk(main_url, site_url, file_name, folder_url, upload_id, chunk, offset, headers, cookies)
                offset += chunk_size

            # Finish upload
            chunk = file.read(chunk_size)
            finish_upload(main_url, site_url, file_name, upload_id, chunk, offset,  headers, cookies)
        except Exception as e:
            print(f'\n\n\tThere was an issue\n {e} \n')

        

def main():
    
    # SharePoint site URL
    main_url = 'https://webmailbyui.sharepoint.com/'
    site_url = 'sites/UniversityCommunicationsAnalytics'

    current_location = os.path.dirname(os.path.realpath(__file__))

    # Path to the file you want to upload
    file_path = current_location + '/results/recent_site_scan.json'

    # SharePoint folder where you want to upload the file
    folder_url = f"Shared%20Documents%2FSharepoint%20upload%20test"


    cookies={
        'MicrosoftApplicationsTelemetryDeviceId':'c524bdf4-cbc2-4661-a828-25e7592fa82c',
        'MSFPC': 'GUID=1d79678b57d549a39e5be3846a2debc1&HASH=1d79&LV=202309&V=4&LU=1695658241343',
        'WordWacDataCenter':'PUS7',
        'ExcelWacDataCenter':'PUS7',
        'WacDataCenter':'PUS7',
        'OneNoteWacDataCenter':'PUS7',
        'SIMI':'eyJzdCI6MH0=',
        'rtFa':'/zTo7PJen4Vh5VegFrzrBUCqyXvOG9+XzFkbmTAEHDEmZTZhYzFkMWYtZDY5NS00ZWYxLTkxZDQtOTRjZGRlZjhiZTExIzEzMzUzNzA2Mzg2MTc3NjA3OCMzNjg2MTBhMS0yMDJkLTUwMDAtMGRmYi03NjU0ZTBmNWI4N2EjYW5kcmVyZWdpbm8lNDBieXVpLmVkdSMxOTIwNzEjdnRHQ2JlVEdQZGlzUUtlaHZFc1BGLTFhTUpJErZ56HNmg3BSwlbv5gbPMqegyqo8UtjWjTonBwExMysWj+Hj2ul/UmzN+iVo3G4ymyF7xvnU/FxJCqXmeJN2xPoHrmDmWUF0bv6rjXRGmVZxyUVETXB/vb6CAYViRg1bd2RzbZXMAyQAy9Ce9jXNlUsWVjnr7skGa80sgg1GNZ0t3ijySJ5DupOhXmLD7S3IoowWC4Z3jn7bFSffdU6XHt7Of2deApSplzzC7vSYz2lTSgAvU/sWy27x//3cxeVPwai7TPAvUgQ/DtgsmqmLdpoN6zR9RJD1WZBiNtSYpivdMFTPmGwmmrKexo6UHwVKZhQ+O7CCgizVLykwlDHvz7cAAAA=',
        'FedAuth':'77u/PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48U1A+VjEzLDBoLmZ8bWVtYmVyc2hpcHwxMDAzMjAwMTYwZmJiNGE5QGxpdmUuY29tLDAjLmZ8bWVtYmVyc2hpcHxhbmRyZXJlZ2lub0BieXVpLmVkdSwxMzM1MzcwNTcxNjAwMDAwMDAsMTMzMzQwMDYxMDAwMDAwMDAwLDEzMzU0NzM5Mjg3MTg4Nzk2NiwxNTcuMjAxLjk2LjY5LDIsZTZhYzFkMWYtZDY5NS00ZWYxLTkxZDQtOTRjZGRlZjhiZTExLCw4ZTM4YjUwMC1jMWFlLTQzMWYtODg2NC01ZGE1NzNiZmRiOTgsMzY4NjEwYTEtMjAyZC01MDAwLTBkZmItNzY1NGUwZjViODdhLGRkMGMxNGExLTUwODctNDAwMC1mZmE0LTA2MGZiZTA5Nzg5NiwsMCwxMzM1NDY1NDQ4MjM2MDI5MTcsMTMzNTQ5MTAwODIzNjAyOTE3LCwsZXlKNGJYTmZZMk1pT2lKYlhDSkRVREZjSWwwaUxDSjRiWE5mYzNOdElqb2lNU0lzSW5CeVpXWmxjbkpsWkY5MWMyVnlibUZ0WlNJNkltRnVaSEpsY21WbmFXNXZRR0o1ZFdrdVpXUjFJaXdpZFhScElqb2lObXRhYmxkVlkwbElhMHRhY1ZOV1RITk5WMGRCUVNKOSwyNjUwNDY3NzQzOTk5OTk5OTk5LDEzMzUzNzA2Mzg1MDAwMDAwMCw2YTM2MmM1Mi00MDUxLTQ1NDctOWY1NS00N2JkM2Q5OGYwYWMsLCwsLCwwLCwxOTIwNzEsRGFEQWZqUVFtcHlPWHgyUnJLX1c1bHZvTFo0LHJaM0k3UUNVWWlsS090eEJydU5pS21wM1BSNTUwTVBCM1oxLy8xT1UzWUJDU09uYUlwVjZnaE9jTmNScFEybllTSmVJay82RXRrSHp3VXp0NUZaeGo2VUU5RXNPOFNsOElnYmM3Znk3UnJDR1FZK3NoSVEzalcxNEQrQ3A3K1FNOTFYdDg5UkpUNThyaDlMbEtvNDFxSmV0dGQrM2hjUWkwazFTTE9DSE5wWUpQd1RVNVQzUVlEQlg1RFZUNVpSUWR2YUlweTdsQ3UyY3ZlQm9GQzZZZUlrd2RmcjRXQnJETjJKam0xNU9oT05UQTd1Tk02TCtTK2lPQUVmTGl2UWxyT2NjcjA4djlWZkVyVEJrSHE0NDhVcmVMVXptc01aRFdsLzVWRlg0U2l2eDY4YzluMHBTZW9vd2pIcTgxRjk4aGJOL3BzTEJWYlhYQUxIVHJtaEUxQT09PC9TUD4=',
        'ai_session':'uDsiXLM339mIb9ykGNf/0b|1710169567702|1710179894894'
            
    }
    
    # SharePoint requires specific headers
    headers = {
        'Accept': 'application/json; odata=verbose',
        'Content-Type': 'application/json; odata=verbose',
    }


    file_size = os.path.getsize(file_path)
    
    add_context(main_url, site_url, headers, cookies)


    if file_size < 200000000:
        upload_small_file(main_url, site_url, folder_url, file_path, headers, cookies)
    else:
        # Perform chunked upload
        chunked_upload(main_url, file_path, site_url, folder_url, headers, cookies)

        
# This is mostly good practice, this runs the main function 
# only if we are in the main thread.

main()