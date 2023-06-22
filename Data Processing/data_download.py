import requests
import json
import pandas as pd
import csv

response = requests.get('https://developer.nrel.gov/api/alt-fuel-stations/v1.csv?api_key=RZz4lKNHQOyzEmMlXG0MjoZytR1OrxKVM4dZ3bg8&fuel_type=ELEC')

myreader = csv.reader(response.text.splitlines())
data_list = []
for row in myreader:
    data_list += [row]

with open('outputdata.csv', 'w') as outfile:
    mywriter = csv.writer(outfile)
    for d in data_list:
        mywriter.writerow(d)