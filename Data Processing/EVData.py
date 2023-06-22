import requests
import wget
import httplib2
from bs4 import BeautifulSoup, SoupStrainer
import re
import os
import urllib
from zipfile import ZipFile

url="https://www.fhwa.dot.gov/policyinformation/tables/tmasdata/"

links=[]
http = httplib2.Http()
status, response = http.request(url)

for link in BeautifulSoup(response, parse_only=SoupStrainer('a'),features='html.parser'):
    if link.has_attr('href') and ".zip" in link['href']:
        links.append(link['href'])

#print(links)
ypattern="(\d\d\d\d)/"
mpattern="_(.*?)\.zip"
for l in links:
    year=re.search(ypattern,l).groups()[0]
    month=re.search(mpattern,l).groups()[0]
    folder=year
    if not os.path.exists(year):
        os.makedirs(year)
    destination=year
    zip_path, _ = urllib.request.urlretrieve(url+l)
    with ZipFile(zip_path, "r") as f:
        f.extractall(destination)