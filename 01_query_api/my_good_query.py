import os  # for reading environment variables
import requests  # for making HTTP requests
from dotenv import load_dotenv  # for loading variables from .envload_dotenv(".env")



## 1. Make API Request ###########################

# Execute query to get time series data from the API
response = requests.get(
    "https://api.carbonintensity.org.uk/intensity/2017-09-18T11:30Z/2017-09-20T12:00Z" #API key is not required for this API.
)

## 2. Inspect Response ###########################
if(response.status_code == 200):
    print("Request successful")
elif(response.status_code == 400):
    print({'error': {'code': '400 Bad Request', 'message': 'Please enter a valid start and end datetime in ISO8601 format YYYY-MM-DDThh:mmZ i.e. /intensity/2017-08-25T15:30Z/2017-08-27T17:00Z'}})
else:
    print({'error': {'code': '500 Internal Server Error'}})


print(response.json())