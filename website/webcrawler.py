import requests
from bs4 import BeautifulSoup
import urllib.request
from urllib.request import urlopen

#base url to append link if the path is relative
#BASE_URL = 'https://makeabilitylab-test.cs.washington.edu/media/'
BASE_URL = ''


def getLinks(url, split_by='\"'):
    source_code = requests.get(url)
    plain_text = source_code.text
    soup = BeautifulSoup(plain_text, 'html.parser')
    for link in soup.findAll('a', {'class': 'js-navigation-open'}):
        print(link.title)

    #for item in a:
    #    #insert string that's part of the link you want
    #    if '' not in item:
    #        continue
    #    else:
    #        urls.add(item)
    #        print(item)
    ##formatting relative path, set if unique, list if all retain
    #urls = set(map(lambda s : s.replace('../', ''), urls))
    #return urls

url = "https://github.com/jonfroehlich/makeabilitylabwebsite/tree/master/import/images/StarWarsFiguresFullSquare/Rebels"


urls = getLinks(url)







