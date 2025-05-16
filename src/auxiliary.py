import random
import re
import os
from datetime import date

import requests
from bs4 import BeautifulSoup
import time

from globalVariables import fileNameChartLinks, fileSongsNotListened, fileSongsListened, urlSongCharts, \
    fileChartProperties, SCORE_NUMERATOR, SCORE_DENOMINATOR, SCORE_RATING_INERTIA, MIN_SLEEP_BETWEEN_CHARTS, \
    MAX_SLEEP_BETWEEN_CHARTS, headerFile


def removeURLImpurities(link: str):
    link = re.sub(r'&', '', link)
    link = re.sub(r'#', '', link)
    return link


def parseLinkName(linkName: str):
    linkName = re.sub(r'-\d+', '', linkName)
    linkName = re.sub(r'-country', '', linkName)
    linkName = re.sub(r'-hotw', '', linkName)
    linkName = re.sub(r'-hot', '', linkName)
    linkName = re.sub(r'-top', '', linkName)
    linkName = re.sub(r'top-', '', linkName)
    linkName = re.sub(r'-songs', '', linkName)
    linkName = re.sub(r'-albums', '', linkName)
    linkName = re.sub(r'official-', '', linkName)
    linkName = re.sub(r'billboard-', '', linkName)
    linkName = re.sub(r'-billboard', '', linkName)
    linkName = re.sub(r'&', ' ', linkName)
    linkName = re.sub(r';', ' ', linkName)
    return linkName


def sleep():
    '''Protect against being banned from web scrapping'''
    delay = random.uniform(MIN_SLEEP_BETWEEN_CHARTS, MAX_SLEEP_BETWEEN_CHARTS)  # Delay between 1 and 5 seconds
    time.sleep(delay)


def writeChartLinksToFile():
    response = requests.get(urlSongCharts)
    soup = BeautifulSoup(response.text, 'html.parser')

    linkAddresses = []
    for link in soup.find_all('a', href=True):
        if "charts" in link['href'] and link['href'].find('www.billboard.com/charts/') != -1:
            linkAddresses.append(link['href'])
    linkAddresses = list(set(linkAddresses))

    patternLinkName = r'charts/([a-zA-Z0-9-]+)/'
    with open(fileNameChartLinks, 'w') as the_file:
        for link in linkAddresses:

            linkName = re.search(patternLinkName, link)
            if linkName:
                linkName = linkName.groups()[0]
            else:
                raise Exception("No match found in " + link)

            isAlbum = re.search(r'album', linkName)
            isArtist = re.search(r'artist', linkName)
            if isAlbum or isArtist:
                continue

            linkName = parseLinkName(linkName)

            the_file.write(link + "," + linkName + "\n")

    sleep()


def getChartLinksFromFile():
    countries = {}
    with open(fileNameChartLinks, 'r') as the_file:
        lines = the_file.readlines()
        for line in lines:
            found = line.split(";")
            if found:
                found[1] = re.sub(r'\n', '', found[1])
                countries[found[1]] = found[0]
            else:
                raise Exception("Wrong line in country links file. Line: " + line)

    return countries


def getScore(song, app) -> int:
    if song['chart'] in app.chartProperties:
        chart = app.chartProperties[song['chart']]
        if 'rating' in chart:
            rating = app.chartProperties[song['chart']]['rating']
            score = int(SCORE_NUMERATOR / (SCORE_DENOMINATOR + int(song['rank']))
                       * (SCORE_RATING_INERTIA + float(rating)))
            return score
        else:
            raise Exception(chart + " does not have a rating")
    else:
        raise Exception(song['chart'] + " is not in chartProperties")


def ensure_csv_files_exist():
    """
    Ensures that the songsNotListened.csv and songsListened.csv files exist.
    If they don't exist, creates them with the appropriate header.
    """
    for file_path in [fileSongsNotListened, fileSongsListened]:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write(headerFile + "\n")


def getSongsNotListened(app):
    songsNotListened = []
    ensure_csv_files_exist()
    with open(fileSongsNotListened, 'r') as fileNotListened:
        headers = fileNotListened.readline().strip().split(';')
        songsNotListenedFile = fileNotListened.readlines()
        for song in songsNotListenedFile:
            properties = song.strip().split(';')
            song = {headers[i]: properties[i] for i in range(len(headers))}
            song['score'] = getScore(song, app)
            songsNotListened.append(song)

    return songsNotListened


def getChartProperties():
    chartProperties = {}
    with open(fileChartProperties, 'r') as fileProperties:
        headers = fileProperties.readline().strip().split(';')
        linesChartProps = fileProperties.readlines()
        for chartProps in linesChartProps:
            properties = chartProps.strip().split(';')
            if properties[1] == "":
                properties[1] = 0
            chartProperties[properties[0]] = {'rating': properties[1], 'maxRank': properties[2]}

    return chartProperties


def sortBillBoardChartLinksByChartRepresented(countries):
    sortedCountries = dict(sorted(countries.items(), key=lambda item: item[0]))
    with open("billboardChartLinks2.csv", "w+") as g:
        for chartURL, chart in sortedCountries.items():
            g.write(chart + ";" + chartURL + "\n")


def generateYoutubeLink(songName, artist):
    songNameURL = re.sub(r' ', '+', songName)
    artistURL = re.sub(r' ', '+', artist)
    youtubeLink = 'https://music.youtube.com/search?q=' + artistURL + "+" + songNameURL
    return removeURLImpurities(youtubeLink)
