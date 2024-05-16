import functools
import math
import os
import re
import webbrowser
from datetime import date

import customtkinter as ctk
import requests
from bs4 import BeautifulSoup
from PIL import Image
from tktooltip import ToolTip

from src.auxiliary import getChartLinksFromFile, getSongsNotListened, sleep, removeURLImpurities, \
    getChartProperties
from src.globalVariables import fileSongsListened, fileSongsNotListened, headerFile, column_widths, maxArtistLength, \
    maxSongLength, ICON_SIZE, PAGE_SIZE_SONG, headerGUI, NO_SONGS_LAST, fileChartCount, btnRanks, \
    MAX_SONG_COMPONENT_SIZE, SONG_TABLE_OFFSET_ROW, SONG_TABLE_OFFSET_COLUMN, CHART_TABLE_OFFSET_COLUMN, \
    CHART_TABLE_OFFSET_ROW


class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Top WorldWide Song Finder")
        self.geometry("1400x900")
        for col, width in enumerate(column_widths):
            self.grid_columnconfigure(col, minsize=width)
        ctk.set_appearance_mode("dark")

        self.pageSongNotListened = 0
        self.pageSongListened = 0
        self.pageNoChart = 0
        self.widgetsChart = []
        self.widgetsSongs = []
        self.chartLengths = {}
        self.showListenedSongs = False

        self.countries = getChartLinksFromFile()
        self.chartProperties = getChartProperties()
        self.songsNotListened = getSongsNotListened(self)
        self.songsListened = getSongsListened()
        self.pageSongListened = math.ceil(len(self.songsListened) / PAGE_SIZE_SONG) - 1 # set the page of listened songs to the last one
        sortSongsBy(self, 'score')
        self.populateSongs()
        self.populateCharts()

    def populateSongs(self):

        for widget in self.widgetsSongs:
            widget.destroy()
        self.widgetsSongs.clear()

        text = "Show new songs" if self.showListenedSongs else "Show listened words"
        btnSwitch = ctk.CTkButton(master=self, text=text, fg_color='purple',
                                 command=functools.partial(switchSongs, self))
        btnSwitch.grid(row=0, column=0)
        self.widgetsSongs.append(btnSwitch)

        text = "Listened songs so far" if self.showListenedSongs else "Discoverable songs"
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

            lblArtist = ctk.CTkLabel(master=self, text=song['artist'][:maxArtistLength], justify=ctk.RIGHT)
            lblArtist.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 0, pady=2)
            self.widgetsSongs.append(lblArtist)

            lblSongName = ctk.CTkLabel(master=self, text=song['songName'][:maxSongLength], justify=ctk.RIGHT)
            lblSongName.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 1)
            self.widgetsSongs.append(lblSongName)

            image = getImageFromChart(song['chart'])

            text = song['chart'] if image is None else ""
            lblChart = ctk.CTkLabel(master=self, text=text, justify=ctk.RIGHT, compound="right", anchor="w",
                                    image=image, font=("Arial", 50))
            lblChart.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 2)
            ToolTip(lblChart,
                    msg='Chart: ' + song['chart'] + "; Rating: " + str(self.chartProperties[song['chart']]['rating']),
                    delay=0, fg="#ffffff", bg="#1c1c1c")
            self.widgetsSongs.append(lblChart)

            lblRank = ctk.CTkLabel(master=self, text=song['rank'], justify=ctk.RIGHT)
            lblRank.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 3)
            self.widgetsSongs.append(lblRank)

            text = "\u25B6"  #  + str(song['score'])
            btnListen = ctk.CTkButton(master=self, text=text, fg_color="red",
                                      command=functools.partial(openYoutubeLink, songID, self))
            btnListen.grid(row=SONG_TABLE_OFFSET_ROW + renderID, column=SONG_TABLE_OFFSET_COLUMN + 4)
            self.widgetsSongs.append(btnListen)

        text = "Last page" if self.showListenedSongs else "First page"
        column = SONG_TABLE_OFFSET_COLUMN + 4 if self.showListenedSongs else SONG_TABLE_OFFSET_COLUMN + 0
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

        topButtonCount = len(btnRanks)
        for rankID, maxRank in enumerate(btnRanks):
            btnTop = ctk.CTkButton(master=self, text='Top ' + str(maxRank), fg_color='purple',
                                   command=functools.partial(getSongsFromCountries, self, maxRank))
            btnTop.grid(row=rowOffset + rankID, column=columnOffset)

        combobox = ctk.CTkComboBox(self, values=list(self.countries))  # command=combobox_callback)
        combobox.grid(row=rowOffset, column=columnOffset + 1)
        self.widgetsChart.append(combobox)


def openYoutubeLink(songID, app):
    def callback():
        webbrowser.open(app.songsNotListened[songID]['urlYoutube'])
        with open(fileSongsListened, 'a') as fileListened, open(fileSongsNotListened, 'w') as fileNotListened:
            id = -1
            fileNotListened.write(headerFile + "\n")
            for song in app.songsNotListened:
                id += 1
                listened = id == songID
                # if listened:
                #     print('Will delete: ' + str(song))
                if not listened:
                    song['urlYoutube'] = removeURLImpurities(song['urlYoutube'])
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


def getSongsFromCountries(self, maxRank):
    def callback():
        open(fileChartCount, 'w').close()  # erase count of charts' length
        for nextChart in self.countries:
            getSongsFromWebChart(self, nextChart, maxRank)

    callback()
    self.songsNotListened = getSongsNotListened(self)
    self.populateSongs()


def getSongsFromWebChart(self, chart, maxRank):
    def callback():
        sleep()
        url = self.countries[chart]
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        divName = 'chart-results-list'
        containerSongs = soup.find('div', class_=divName)
        li_elements = containerSongs.find_all('li')
        stringToAddToNotListened = ""
        rank = 0
        with open(fileSongsNotListened, 'r') as fileNotListened:
            songsNotListened = fileNotListened.readlines()
            for li in li_elements:
                children = list(li.children)
                if len(children) != 5:
                    continue
                # tags = [child for child in children if isinstance(child)]
                h3 = li.find('h3')
                span = li.find('span')
                if h3 and span:
                    rank += 1
                    if rank > maxRank:
                        continue
                    songName = re.sub('\s+', ' ', h3.text).strip()
                    artist = re.sub('\s+', ' ', span.text).strip()
                    songNameURL = re.sub(r' ', '+', songName)
                    artistURL = re.sub(r' ', '+', artist)
                    youtubeURL = 'https://www.youtube.com/results?search_query=' + artistURL + "+" + songNameURL + "+lyrics"

                    skip = False
                    # Check if the song has been listened
                    for song in self.songsListened:
                        if artist == song['artist'] and songName == song['songName']:
                            skip = True
                            break
                    if skip:
                        continue
                    for songLine in songsNotListened:
                        songProperties = songLine.split(";")
                        artistFile = songProperties[0]
                        songNameFile = songProperties[1]
                        if artist == artistFile and songName == songNameFile:
                            skip = True
                            continue
                    if skip:
                        continue
                    stringToAddToNotListened += artist + ";" + songName + ";" + str(
                        rank) + ";" + chart + ";" + str(date.today()) + ";" + youtubeURL + "\n"

        if rank == 0:
            print("No songs found in the chart" + chart)
        else:
            with open(fileChartCount, 'a') as f:
                f.write(chart + ";" + str(rank) + ";\n")
        with open(fileSongsNotListened, 'a') as fileNotListened:
            fileNotListened.write(stringToAddToNotListened)

        if maxRank == 999:
            self.songsNotListened = getSongsNotListened(self)
            self.populateSongs()

        print('Got songs from ' + chart)

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
        targetSongList = app.songsListened if app.showListenedSongs else app.songsNotListened
        lastPage = math.ceil(len(targetSongList) / PAGE_SIZE_SONG)
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
    path = "./resources/" + chart + ".png"
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
        app.populateSongs()
    return callback()