import requests

params = {'status': 'Half Full'}
response = requests.get('https://nameless-lake-00313.herokuapp.com/report/1/', params=params)

print(response.url)