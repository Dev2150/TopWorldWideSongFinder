import functools
import math
import os
import re
import webbrowser
import asyncio
import customtkinter as ctk
import requests
from auxiliary import getChartLinksFromFile, getSongsNotListened, sleep, getChartProperties, generateYoutubeLink, ensure_csv_files_exist
from globalVariables import fileSongsListened, fileSongsNotListened, headerFile, columnWidths, maxArtistLength, \
    maxSongLength, ICON_SIZE, PAGE_SIZE_SONG, headerGUI, NO_SONGS_LAST, fileChartCount, rankList, \
    MAX_SONG_COMPONENT_SIZE, SONG_TABLE_OFFSET_ROW, SONG_TABLE_OFFSET_COLUMN, CHART_TABLE_OFFSET_COLUMN, \
    CHART_TABLE_OFFSET_ROW, column_widths2, TOOLTIP_ALPHA, IS_AFFECTED_BY_RATING, SCORE_RATING_INERTIA, \
    SCORE_DENOMINATOR, PRINT_CHART_STATISTICS, URL_LAST_FM_CHARTS, LAST_FM_SONG_TR_CLASS, VERBOSE
from bs4 import BeautifulSoup
from PIL import Image
from CTkToolTip import *
from datetime import date
from shazamio import Shazam
from globalVariables import genresShazam, countryCodesShazam


class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Top WorldWide Song Finder")
        self.geometry("1400x900")
        for col, width in enumerate(columnWidths):
            self.grid_columnconfigure(col, minsize=width)
        ctk.set_appearance_mode("dark")

        self.pageSongNotListened = 0
        self.pageSongListened = 0
        self.pageNoChart = 0
        self.widgetsChart = []
        self.widgetsSongs = []
        self.chartLengths = {}
        self.showListenedSongs = False

        # Ensure CSV files exist before loading data
        ensure_csv_files_exist()
        
        self.countries = getChartLinksFromFile()
        self.chartProperties = getChartProperties()
        self.songsNotListened = getSongsNotListened(self)
        self.songsListened = getSongsListened()
        self.pageSongListened = math.ceil(len(self.songsListened) / PAGE_SIZE_SONG) - 1  # set the page of listened songs to the last one
        sortSongsBy(self, 'score')
        self.populateSongs()
        self.populateCharts()

        btnDuplicates = ctk.CTkButton(master=self, text="Print duplicates", fg_color='red',
                                      command=functools.partial(findDuplicates, self))
        btnDuplicates.grid(row=0, column=7)
        btnStats = ctk.CTkButton(master=self, text="Print statistics", fg_color='red',
                                 command=functools.partial(printStatistics, self))
        btnStats.grid(row=1, column=7)

        btnPlayNext5 = ctk.CTkButton(master=self, text="Play next 5 songs", fg_color="#6b03fc",
                                     command=functools.partial(openYoutubeLink, self, 0, 5))
        btnPlayNext5.grid(row=2, column=4)

    def populateSongs(self):

        for widget in self.widgetsSongs:
            widget.destroy()
        self.widgetsSongs.clear()

        text = "Show new songs" if self.showListenedSongs else "Show listened songs"
        btnSwitch = ctk.CTkButton(master=self, text=text, fg_color='purple',
                                  command=functools.partial(switchSongs, self))
        btnSwitch.grid(row=0, column=0)
        self.widgetsSongs.append(btnSwitch)

        if self.showListenedSongs:
            text = str(len(self.songsListened)) + " Listened songs so far (p. " + str(self.pageSongListened + 1)
        else:
            text = str(len(self.songsNotListened)) + " Discoverable songs (p. " + str(self.pageSongNotListened + 1)
        text += " / " + str(getMaxPage(self)) + ")"
        lblTableTitle = ctk.CTkLabel(master=self, text=text, justify=ctk.RIGHT, font=("Arial", 20))
        lblTableTitle.grid(row=1, column=0, pady=2, columnspan=5)
        self.widgetsSongs.append(lblTableTitle)

        targetSongList = self.songsListened if self.showListenedSongs else self.songsNotListened
        page = self.pageSongListened if self.showListenedSongs else self.pageSongNotListened

        start = 0 + page * PAGE_SIZE_SONG
        end = min(0 + (page + 1) * PAGE_SIZE_SONG, len(targetSongList))
        for songID in range(start, end):
            song = targetSongList[songID]
            renderID = songID - start + 1
            for col, header in enumerate(headerGUI):
                label = ctk.CTkLabel(self, text=header, padx=10, pady=5, fg_color="gray")
                label.grid(row=SONG_TABLE_OFFSET_ROW, column=SONG_TABLE_OFFSET_COLUMN + col, padx=5, pady=5,
                           sticky="nsew")
                self.widgetsSongs.append(label)

            background = "#333333" if renderID % 2 == 0 else "transparent"

            frameArtist = ctk.CTkFrame(master=self, fg_color=background)
            frameArtist.grid(
                row=SONG_TABLE_OFFSET_ROW + renderID,
                column=0,
                columnspan=5,
                sticky="w"
            )
            self.widgetsSongs.append(frameArtist)
            for col, width in enumerate(column_widths2):
                frameArtist.grid_columnconfigure(col, minsize=width)

            lblArtist = ctk.CTkLabel(master=frameArtist, text=song['artist'][:maxArtistLength], anchor="w")
            lblArtist.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 0, pady=2)
            self.widgetsSongs.append(lblArtist)

            lblSongName = ctk.CTkLabel(master=frameArtist, text=song['songName'][:maxSongLength], anchor="w")
            lblSongName.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 1)
            self.widgetsSongs.append(lblSongName)

            image = getImageFromChart(song['chart'])

            text = song['chart'] if image is None else ""
            lblChart = ctk.CTkLabel(master=frameArtist, text=text, justify=ctk.RIGHT, compound="right",
                                    image=image, font=("Arial", 50))
            lblChart.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 2)
            self.widgetsSongs.append(lblChart)
            tlt = CTkToolTip(lblChart,
                             message='Chart: ' + song['chart'] + "\nRating: " + str(
                                 self.chartProperties[song['chart']]['rating']),
                             delay=0, justify="left", alpha=TOOLTIP_ALPHA)
            self.widgetsSongs.append(tlt)

            lblRank = ctk.CTkLabel(master=frameArtist, text=song['rank'], justify=ctk.RIGHT)
            lblRank.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 3)
            self.widgetsSongs.append(lblRank)

            if not self.showListenedSongs:
                text = "\u25B6"  # + str(song['score'])
                fg_color = "red"
                btnListen = ctk.CTkButton(master=frameArtist, text=text, fg_color=fg_color,
                                          command=functools.partial(openYoutubeLink, self, songID, 1))
                btnListen.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 4)
                self.widgetsSongs.append(btnListen)
                tlt = CTkToolTip(btnListen,
                                 message='Score: ' + str(song['score']),
                                 delay=1, justify="left", alpha=TOOLTIP_ALPHA)
                self.widgetsSongs.append(tlt)

        text = "Last page" if self.showListenedSongs else "First page"
        column = SONG_TABLE_OFFSET_COLUMN + 0  # if not self.showListenedSongs else SONG_TABLE_OFFSET_COLUMN + 4
        btnTop = ctk.CTkButton(master=self, text=text, fg_color='#dd7700',
                               command=functools.partial(changePageSong, self, 0))
        btnTop.grid(row=2, column=column)
        self.widgetsSongs.append(btnTop)

        btnPrev = ctk.CTkButton(master=self, text='<', fg_color='orange',
                                command=functools.partial(changePageSong, self, -1))
        btnPrev.grid(row=2, column=SONG_TABLE_OFFSET_COLUMN + 1)
        self.widgetsSongs.append(btnPrev)

        btnNext = ctk.CTkButton(master=self, text='>', fg_color='orange',
                                command=functools.partial(changePageSong, self, +1))
        btnNext.grid(row=2, column=SONG_TABLE_OFFSET_COLUMN + 2)
        self.widgetsSongs.append(btnNext)

        btnSortByRank = ctk.CTkButton(master=self, text='Sort by rank', fg_color='maroon1',
                                      command=functools.partial(sortSongsBy, self, 'rank'))
        btnSortByRank.grid(row=0, column=1)
        self.widgetsSongs.append(btnSortByRank)

        btnSortByChart = ctk.CTkButton(master=self, text='Sort by chart', fg_color='maroon1',
                                       command=functools.partial(sortSongsBy, self, 'chart'))
        btnSortByChart.grid(row=0, column=2)
        self.widgetsSongs.append(btnSortByChart)

        btnSortByScore = ctk.CTkButton(master=self, text='Sort by score', fg_color='maroon1',
                                       command=functools.partial(sortSongsBy, self, 'score'))
        btnSortByScore.grid(row=0, column=4)
        self.widgetsSongs.append(btnSortByScore)

    def populateCharts(self):

        rowOffset = CHART_TABLE_OFFSET_ROW
        columnOffset = CHART_TABLE_OFFSET_COLUMN
        for widget in self.widgetsChart:
            widget.destroy()
        self.widgetsChart.clear()

        for rankID, maxRank in enumerate(rankList):
            btnTop = ctk.CTkButton(master=self, text='Top ' + str(maxRank), fg_color='purple',
                                   command=functools.partial(getSongsFromWWW, self, maxRank))
            btnTop.grid(row=rowOffset + rankID, column=columnOffset)

        combobox = ctk.CTkComboBox(self, values=list(self.countries))  # command=combobox_callback)
        combobox.grid(row=rowOffset, column=columnOffset + 1)
        self.widgetsChart.append(combobox)


def openYoutubeLink(app, pSongID, songsToPlay=1):
    def callback():

        songList = list(range(pSongID, min(pSongID + songsToPlay, len(app.songsNotListened))))

        ensure_csv_files_exist()
        with open(fileSongsListened, 'a') as fileListened, open(fileSongsNotListened, 'w') as fileNotListened:
            for songID in songList:
                webbrowser.open(app.songsNotListened[songID]['urlYoutube'])

            id = -1
            fileNotListened.write(headerFile + "\n")
            for song in app.songsNotListened:
                id += 1
                listened = id in songList

                if not listened:
                    # song['urlYoutube'] = removeURLImpurities(song['urlYoutube'])
                    songString = song['artist'] + ";" + song['songName'] + ";" + str(
                        song['rank']) + ";" + song['chart'] + ";" + song['date'] + ";" + song[
                                     'urlYoutube'] + "\n"
                    fileNotListened.write(songString)
                else:
                    songString = song['artist'] + ";" + song['songName'] + ";" + str(
                        song['rank']) + ";" + song['chart'] + ";" + str(date.today()) + ";" + song[
                                     'urlYoutube'] + "\n"
                    fileListened.write(songString)

        app.songsNotListened = getSongsNotListened(app)
        app.songsListened = getSongsListened()
        app.populateSongs()

    return callback()


def getSongsFromWWW(self, maxRank):
    def callback():
        if PRINT_CHART_STATISTICS:
            open(fileChartCount, 'w').close()  # erase count of charts' length
        getShazamTopSongsWrapper(self, maxRank)
        print("Got shazam songs")
        for nextChart in self.countries:
            getSongsFromBillboard(self, nextChart, maxRank)
        # getLastFMCharts(self, maxRank)

    callback()
    # self.songsNotListened = getSongsNotListened(self)  # now it's performed inside getSongsFromBillboard
    self.populateSongs()


def getMaxRankBasedOnRating(initialRank, rating):
    result = initialRank
    if IS_AFFECTED_BY_RATING:
        result = ((SCORE_RATING_INERTIA + rating) / SCORE_RATING_INERTIA) * (
                SCORE_DENOMINATOR + initialRank) - SCORE_DENOMINATOR
        result = round(result)
    return result


def getSongsFromBillboard(self, chart, pMaxRank):
    def callback():
        try:
            sleep()
            url = self.countries[chart]
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            divName = 'chart-results-list'
            containerSongs = soup.find('div', class_=divName)
            li_elements = containerSongs.find_all('li')
            stringToAddToNotListened = ""
            rank = 0

            rating = float(self.chartProperties[chart]['rating'])
            maxRank = getMaxRankBasedOnRating(pMaxRank, rating)
            songsFound = 0
            for li in li_elements:
                children = list(li.children)
                if len(children) != 5:
                    continue
                h3 = li.find('h3')
                span = li.find('span')
                if h3 and span:
                    rank += 1
                    if rank > maxRank:
                        continue
                    songName = re.sub(r'\s+', ' ', h3.text).strip()
                    artist = re.sub(r'\s+', ' ', span.text).strip()
                    youtubeURL = generateYoutubeLink(songName, artist)

                    stringToAdd = addToWriteStringIfSongDoesNotExist(self, artist, songName, rank, chart,
                                                                                   youtubeURL)
                    if stringToAdd != "":
                        songsFound += 1
                        stringToAddToNotListened += stringToAdd

            updateSongDatabase(self, rank, chart, maxRank, stringToAddToNotListened, songsFound)
        except AttributeError as e:
            print(f"Attribute Error: {e}")
        except Exception as e:
            print(f"{e}")

    callback()


def changePageChart(app, direction):
    def callback():
        targetPage = (app.pageNoChart + direction) % math.ceil(len(app.countries) / app.stepSizeChart)
        app.pageNoChart = targetPage
        app.populateCharts()

    return callback()


def changePageSong(app, direction: int):
    def callback():
        currentPage = app.pageSongListened if app.showListenedSongs else app.pageSongNotListened
        lastPage = getMaxPage(app)
        if direction == 0:
            targetPage = lastPage - 1 if app.showListenedSongs else 0
        else:
            targetPage = (currentPage + direction) % lastPage

        if app.showListenedSongs:
            app.pageSongListened = targetPage
        else:
            app.pageSongNotListened = targetPage

        app.populateSongs()

    return callback()


def sortSongsBy(app, criterion):
    def callback():
        isSortReversed = False
        if criterion == 'score':
            isSortReversed = True
        app.songsNotListened.sort(key=lambda x: x[criterion], reverse=isSortReversed)
        app.populateSongs()

    return callback()


def getImageFromChart(chart):
    path = "resources/" + chart + ".png"
    if os.path.exists(path):
        imageRaw = Image.open(path)
        image = ctk.CTkImage(imageRaw)
        image._size = (ICON_SIZE, ICON_SIZE)
        return image
    match chart:
        case _:
            return None
    return ctk.CTkImage(Image.open(path))


def getLastSongsListenedTo(app):
    text = "Last songs listened to:\n\n\n\n"

    for songIndex in range(max(0, len(app.songsListened) - NO_SONGS_LAST), len(app.songsListened)):
        song = app.songsListened[songIndex]
        artist = song['artist']
        songName = song['songName']
        if len(artist) > MAX_SONG_COMPONENT_SIZE:
            artist = artist[:MAX_SONG_COMPONENT_SIZE] + "..."
        if len(songName) > MAX_SONG_COMPONENT_SIZE:
            songName = songName[:MAX_SONG_COMPONENT_SIZE] + "..."
        text += artist + " - " + songName + "  \u25B6  " + "#" + str(song['rank']) + " on " + song['chart'] + "\n\n"

    return text


def getSongsListened():
    songsListened = []
    ensure_csv_files_exist()
    with open(fileSongsListened, 'r') as fileListened:
        headers = fileListened.readline().strip().split(';')
        songsListenedFile = fileListened.readlines()
        for song in songsListenedFile:
            properties = song.strip().split(';')
            song = {headers[i]: properties[i] for i in range(len(headers))}
            songsListened.append(song)

    return songsListened


def switchSongs(app):
    def callback():
        app.showListenedSongs = not app.showListenedSongs
        if app.showListenedSongs:
            app.pageSongListened = getMaxPage(app) - 1
        app.populateSongs()

    return callback()


def findDuplicates(app):
    seen = []
    duplicates = []
    for songToCheck in app.songsNotListened + app.songsListened:
        isDuplicate = False
        for songTuple in seen:
            if songTuple['artist'].lower() == songToCheck['artist'].lower() and songTuple['songName'].lower() == \
                    songToCheck['songName'].lower():
                duplicates.append(songToCheck)
                isDuplicate = True
        if not isDuplicate:
            seen.append(songToCheck)
    if len(duplicates) == 0:
        print("No duplicates")
    else:
        for song in duplicates:
            print(f"{song['artist']} - {song['songName']}")


def getMaxPage(app):
    targetSongList = app.songsListened if app.showListenedSongs else app.songsNotListened
    return math.ceil(len(targetSongList) / PAGE_SIZE_SONG)


def addToWriteStringIfSongDoesNotExist(self, artist, songName, rank, chart, youtubeURL):
    skip = False
    # Check if the song has been listened
    for song in self.songsListened:
        if artist.lower() == song['artist'].lower() and songName.lower() == song['songName'].lower():
            skip = True
            break
    if skip:
        return ''
    for song in self.songsNotListened:
        if artist.lower() == song['artist'].lower() and songName.lower() == song['songName'].lower():
            skip = True
            break
    if skip:
        return ""
    return artist + ";" + songName + ";" + str(
        rank) + ";" + chart + ";" + str(date.today()) + ";" + youtubeURL + "\n"


async def getShazamResultsFromWeb(app, maxRank):
    shazam = Shazam()

    shazamTracks = []
    for genre in genresShazam:
        chart = genre.value + "-worldwide-shazam"
        rating = app.chartProperties[chart]['rating']

        maxRank = getMaxRankBasedOnRating(maxRank, rating)

        topSongsInTheWorld = await shazam.top_world_genre_tracks(genre=genre, limit=maxRank)
        for rank, track in enumerate(topSongsInTheWorld['data']):
            attr = track['attributes']
            songName = attr['name']
            artist = attr['artistName']

            for shazamTrack in shazamTracks:
                if shazamTrack['songName'].lower() != songName.lower() and shazamTrack[
                    'artist'].lower() != artist.lower():
                    shazamTracks.append({
                        'songName': songName,
                        'artist': artist,
                        'chart': chart,
                        'rank': rank + 1,
                        'date': date.today(),
                        'urlYoutube': generateYoutubeLink(songName, artist)
                    })
    for countryCode in countryCodesShazam:
        topSongsInTheWorld = await shazam.top_country_tracks(limit=maxRank, country_code=countryCode)

        for rank, track in enumerate(topSongsInTheWorld['data']):
            attr = track['attributes']
            songName = attr['name']
            artist = attr['artistName']

            for shazamTrack in shazamTracks:
                if shazamTrack['songName'].lower() != songName.lower() and shazamTrack[
                    'artist'].lower() != artist.lower():
                    shazamTracks.append({
                        'songName': songName,
                        'artist': artist,
                        'chart': countryCode + "-shazam",
                        'rank': rank + 1,
                        'date': date.today(),
                        'urlYoutube': generateYoutubeLink(songName, artist)
                    })
    shazamTracks.sort(key=lambda x: x['rank'])
    return shazamTracks


def getShazamTopSongsWrapper(app, maxRank):
    shazamTracks = asyncio.run(getShazamResultsFromWeb(app, maxRank))
    writeMaterial = ""
    for track in shazamTracks:
        writeMaterial += addToWriteStringIfSongDoesNotExist(app, track['artist'], track['songName'], track['rank'],
                                                            track['chart'], track['urlYoutube'])
    ensure_csv_files_exist()
    with open(fileSongsNotListened, 'a') as fileNotListened:
        fileNotListened.write(writeMaterial)


def test(app, track):
    print('Testing\n')
    # writeMaterial = addToWriteStringIfSongDoesNotExist(app, track['artist'], track['songName'], track['rank'],
    #                                                     track['chart'], track['urlYoutube'])
    # print(writeMaterial)


def printStatistics(app):
    dates = {}
    for song in app.songsListened:
        if song['date'] not in dates:
            dates[song['date']] = 0
        else:
            dates[song['date']] += 1
    for date, count in enumerate(dates.items()):
        print(f"{str(date)} - {str(count)}")


def updateSongDatabase(self, rank, chart, maxRank, stringToAddToNotListened, songsFound):
    if rank == 0:
        print(f"No songs found in the chart {chart}")
    else:
        if VERBOSE:
            print(f"Found {str(songsFound): <2} new songs from the {str(maxRank): <2} songs from {chart}")
        else:
            print(f"Found {str(songsFound): <2}/{str(maxRank): <2} songs from {chart}")
        if PRINT_CHART_STATISTICS:
            with open(fileChartCount, 'a') as f:
                f.write(chart + ";" + str(rank) + ";\n")
    ensure_csv_files_exist()
    with open(fileSongsNotListened, 'a') as fileNotListened:
        fileNotListened.write(stringToAddToNotListened)

    self.songsNotListened = getSongsNotListened(self)


def getLastFMCharts(self, maxRank):
    try:
        sleep()
        url = URL_LAST_FM_CHARTS
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        chart = "top-tracks-lastFM"
        tableClassName = 'globalchart'
        containerSongs = soup.find('table', class_=tableClassName)
        li_elements = containerSongs.find_all('tr', class_=LAST_FM_SONG_TR_CLASS)
        stringToAddToNotListened = ""

        # maxRank = getMaxRankBasedOnRating(maxRank, rating)
        rank = 0

        for li in li_elements:
            children = list(li.children)
            if len(children) != 11:
                raise Exception("Last FM on chart not having the expected number of children")
            rank = int(children[1].text.strip())
            songName = children[5].text.strip()
            artist = children[7].text.strip()
            if not isinstance(songName, str) or not isinstance(artist, str):
                raise Exception("Last FM: Expected strings")

            youtubeURL = generateYoutubeLink(songName, artist)

            stringToAddToNotListened += addToWriteStringIfSongDoesNotExist(self, artist, songName, rank, chart,
                                                                           youtubeURL)

        updateSongDatabase(self, rank, chart, maxRank, stringToAddToNotListened)
    except AttributeError as e:
        print(f"Attribute Error: {e}")
    except Exception as e:
        print(f"{e}")