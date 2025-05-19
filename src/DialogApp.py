import functools
import math
import os
import re
import webbrowser
import asyncio
import threading
import json
import customtkinter as ctk
import requests
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from auxiliary import getChartLinksFromFile, getSongsNotListened, sleep, getChartProperties, generateYoutubeLink, ensure_csv_files_exist, get_cached_image
from globalVariables import fileSongsListened, fileSongsNotListened, headerFile, columnWidths, maxArtistLength, \
    maxSongLength, ICON_SIZE, PAGE_SIZE_SONG, headerGUI, NO_SONGS_LAST, fileChartCount, rankList, \
    MAX_SONG_COMPONENT_SIZE, SONG_TABLE_OFFSET_ROW, SONG_TABLE_OFFSET_COLUMN, CHART_TABLE_OFFSET_COLUMN, \
    CHART_TABLE_OFFSET_ROW, column_widths2, TOOLTIP_ALPHA, IS_AFFECTED_BY_RATING, SCORE_RATING_INERTIA, \
    SCORE_DENOMINATOR, PRINT_CHART_STATISTICS, URL_LAST_FM_CHARTS, LAST_FM_SONG_TR_CLASS, VERBOSE
from bs4 import BeautifulSoup
from CTkToolTip import *
from datetime import date, datetime
from shazamio import Shazam
from globalVariables import genresShazam, countryCodesShazam
from google.auth.transport.requests import Request


class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Top WorldWide Song Finder")
        self.geometry("1400x700")
        for col, width in enumerate(columnWidths):
            self.grid_columnconfigure(col, minsize=width)
        ctk.set_appearance_mode("dark")

        # YouTube API setup
        self.youtube = None
        self.playlist_id = self.load_playlist_id()
        self.setup_youtube_api()
        
        self.pageSongNotListened = 0
        self.pageSongListened = 0
        self.pageNoChart = 0
        self.widgetsChart = []
        self.widgetsSongs = []
        self.chartLengths = {}
        self.showListenedSongs = False
        self.songsToPlay = 10  # Default number of songs to play
        
        # Progress indicators
        self.progressFrame = None
        self.progressLabel = None
        self.progressBar = None
        self.isLoading = False
        self.fetchingInterrupted = False
        self.stopButton = None

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

    def setup_youtube_api(self):
        """Setup YouTube API authentication"""
        SCOPES = ['https://www.googleapis.com/auth/youtube']
        creds = None
        
        # Check if we have stored credentials
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
        # If no valid credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secrets.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        self.youtube = build('youtube', 'v3', credentials=creds)
        
    def add_to_playlist(self, video_id):
        """Add a video to the specified playlist"""
        if not self.youtube or not self.playlist_id:
            return False
            
        try:
            request = self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": self.playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        }
                    }
                }
            )
            response = request.execute()
            return True
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return False
            
    def search_video(self, query):
        """Search for a video and return its ID"""
        if not self.youtube:
            return None
            
        try:
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=1
            )
            response = request.execute()
            
            if response['items']:
                return response['items'][0]['id']['videoId']
            return None
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return None

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

            image = get_cached_image(song['chart'])

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

        # Create a frame for the play controls
        playControlFrame = ctk.CTkFrame(master=self, fg_color="transparent")
        playControlFrame.grid(row=2, column=4, padx=5, pady=5)
        self.widgetsSongs.append(playControlFrame)
        
        # Add dropdown for number of songs
        songCountValues = ['5', '10', '25', '50', '100']
        songCountDropdown = ctk.CTkComboBox(master=playControlFrame, values=songCountValues, width=60)
        songCountDropdown.set(str(self.songsToPlay))
        songCountDropdown.grid(row=0, column=0, padx=(0, 5))
        self.widgetsSongs.append(songCountDropdown)
        
        # Update songs to play when dropdown changes
        def update_songs_count(choice):
            self.songsToPlay = int(choice)
        
        songCountDropdown.configure(command=update_songs_count)
        
        # Add play button
        btnPlayNext = ctk.CTkButton(
            master=playControlFrame, 
            text="Add to YT playlist", 
            fg_color="#6b03fc",
            command=lambda: openYoutubeLink(self, 0, open_in_browser=False)
        )
        btnPlayNext.grid(row=0, column=1)
        self.widgetsSongs.append(btnPlayNext)

        # Add browser open button
        btnOpenInBrowser = ctk.CTkButton(
            master=playControlFrame, 
            text="Open in browser", 
            fg_color="#03fc6b",
            command=lambda: openYoutubeLink(self, 0, open_in_browser=True)
        )
        btnOpenInBrowser.grid(row=0, column=2)
        self.widgetsSongs.append(btnOpenInBrowser)

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
        
        # Define consistent sizes
        label_width = 120
        dropdown_width = 150
        button_width = 250
        element_height = 32
        
        # First row - Number of songs label and dropdown
        lblSongCount = ctk.CTkLabel(master=self, text="Number of songs:", font=("Arial", 14), width=label_width, anchor="e")
        lblSongCount.grid(row=rowOffset, column=columnOffset, padx=(5, 10), pady=5, sticky="e")
        self.widgetsChart.append(lblSongCount)
        
        song_count_values = [str(rank) for rank in rankList]
        songCountDropdown = ctk.CTkComboBox(self, values=song_count_values, width=dropdown_width, height=element_height, font=("Arial", 14))
        songCountDropdown.set(str(rankList[0]))  # Set default value to first option
        songCountDropdown.grid(row=rowOffset, column=columnOffset + 1, padx=5, pady=5, sticky="w")
        self.widgetsChart.append(songCountDropdown)
        
        # Second row - Chart selection label and dropdown
        chart_label = ctk.CTkLabel(master=self, text="Select chart:", font=("Arial", 14), width=label_width, anchor="e")
        chart_label.grid(row=rowOffset + 1, column=columnOffset, padx=(5, 10), pady=5, sticky="e")
        self.widgetsChart.append(chart_label)
        
        chartCombobox = ctk.CTkComboBox(self, values=["All Charts"] + list(self.countries), width=dropdown_width, height=element_height, font=("Arial", 14))
        chartCombobox.set("All Charts")  # Default to all charts
        chartCombobox.grid(row=rowOffset + 1, column=columnOffset + 1, padx=5, pady=5, sticky="w")
        self.widgetsChart.append(chartCombobox)
        
        # Third row - Generate button
        btnFrame = ctk.CTkFrame(master=self, fg_color="transparent")
        btnFrame.grid(row=rowOffset + 2, column=columnOffset, columnspan=2, padx=5, pady=10)
        self.widgetsChart.append(btnFrame)
        
        btnGenerate = ctk.CTkButton(
            master=btnFrame, 
            text='Fetch top songs', 
            fg_color='#6b03fc',
            font=("Arial", 14, "bold"),
            width=button_width,
            height=element_height + 8,
            command=lambda: self.generateSongsFromSelection(songCountDropdown, chartCombobox)
        )
        btnGenerate.pack(padx=10, pady=5)
        self.widgetsChart.append(btnGenerate)

        # Add console output text area
        console_frame = ctk.CTkFrame(master=self, fg_color="transparent")
        console_frame.grid(row=rowOffset + 3, column=columnOffset, columnspan=3, rowspan=11, padx=5, pady=5, sticky="nsew")
        self.widgetsChart.append(console_frame)

        # Configure the frame to expand
        console_frame.grid_rowconfigure(0, weight=1)
        console_frame.grid_columnconfigure(0, weight=1)

        self.console_output = ctk.CTkTextbox(
            master=console_frame,
            width=button_width + 20,
            height=500,
            font=("Consolas", 12),
            fg_color="#1a1a1a",
            text_color="#ffffff"
        )
        self.console_output.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.widgetsChart.append(self.console_output)

        # Configure grid weights to allow console to expand
        self.grid_rowconfigure(rowOffset + 3, weight=1)
        self.grid_columnconfigure(columnOffset, weight=1)
        self.grid_columnconfigure(columnOffset + 1, weight=1)

    def show_progress_indicator(self, message="Loading..."):
        # If there's already a progress indicator, destroy it first
        if self.progressFrame is not None:
            self.hide_progress_indicator()
        
        # Create a new progress frame
        self.progressFrame = ctk.CTkFrame(self)
        self.progressFrame.place(relx=0.5, rely=0.5, anchor="center")
        
        self.progressLabel = ctk.CTkLabel(self.progressFrame, text=message, font=("Arial", 14))
        self.progressLabel.pack(pady=(10, 5))
        
        self.progressBar = ctk.CTkProgressBar(self.progressFrame, width=300, mode="indeterminate")
        self.progressBar.pack(padx=20, pady=(0, 10))
        
        # Add a stop button
        self.stopButton = ctk.CTkButton(
            self.progressFrame, 
            text="Stop & Save", 
            font=("Arial", 12),
            fg_color="#ff5555",
            command=self.interrupt_fetching
        )
        self.stopButton.pack(pady=(0, 10))
        
        self.progressBar.start()
        self.progressFrame.lift()
        self.isLoading = True
        self.fetchingInterrupted = False
        self.update()
    
    def hide_progress_indicator(self):
        if self.progressFrame is not None:
            self.progressBar.stop()
            self.progressFrame.destroy()  # Destroy instead of hiding
            self.progressFrame = None
            self.progressLabel = None
            self.progressBar = None
            self.stopButton = None
            self.isLoading = False
            self.update()
    
    def update_progress_message(self, message):
        if self.progressLabel is not None:
            self.progressLabel.configure(text=message)
            self.update()
        # Also update console output
        self.update_console(message)

    def update_console(self, message):
        """Add a message to the console output with timestamp"""
        if hasattr(self, 'console_output'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            self.console_output.insert("end", formatted_message + "\n")
            self.console_output.see("end")  # Scroll to bottom
            self.update()
            
            # Also log to file
            logger = logging.getLogger('TopWorldWideSongFinder')
            logger.info(message)
    
    def refresh_song_data(self):
        """Reload all song data and refresh the UI"""
        # Reload songs from files
        self.songsNotListened = getSongsNotListened(self)
        self.songsListened = getSongsListened()
        
        # Sort songs using current criterion (assumes 'score' is default)
        sortSongsBy(self, 'score')
        
        # Add a small delay to ensure all data is ready
        self.after(100, self._complete_refresh)
    
    def _complete_refresh(self):
        """Complete the UI refresh after data is loaded"""
        # Refresh the UI
        self.populateSongs()
        self.update()
        print("UI refreshed with new songs")

    def generateSongsFromSelection(self, songCountDropdown, chartCombobox):
        # Prevent starting new fetching if already in progress
        if self.isLoading:
            print("Song fetching already in progress")
            return
            
        max_rank = int(songCountDropdown.get())
        selected_chart = chartCombobox.get()
        
        # Show loading indicator
        self.show_progress_indicator("Fetching songs...")
        
        # Run the song fetching in a separate thread
        worker_thread = threading.Thread(
            target=self._fetch_songs_thread,
            args=(selected_chart, max_rank)
        )
        worker_thread.daemon = True
        worker_thread.start()
    
    def _fetch_songs_thread(self, selected_chart, max_rank):
        try:
            if selected_chart == "All Charts":
                # Use the original function to get songs from all charts
                if PRINT_CHART_STATISTICS:
                    open(fileChartCount, 'w').close()  # erase count of charts' length
                
                # Update UI using a function to avoid lambda capture issues
                def update_ui(message):
                    self.after(0, lambda: self.update_progress_message(message))
                
                # Check if we should interrupt after each step
                def should_stop():
                    return self.fetchingInterrupted
                
                update_ui("Getting Shazam songs...")
                if not should_stop():
                    getShazamTopSongsWrapper(self, max_rank)
                
                # Get billboard songs
                total_charts = len(self.countries)
                for i, chart in enumerate(self.countries):
                    if should_stop():
                        update_ui("Interrupted! Saving found songs...")
                        break
                        
                    progress_msg = f"Getting songs from {chart} ({i+1}/{total_charts})"
                    update_ui(progress_msg)
                    getSongsFromBillboard(self, chart, max_rank)
            else:
                # Get songs from only the selected chart
                if PRINT_CHART_STATISTICS:
                    open(fileChartCount, 'w').close()  # erase count of charts' length
                
                # Update UI using a function to avoid lambda capture issues
                def update_ui(message):
                    self.after(0, lambda: self.update_progress_message(message))
                
                # Check if we should interrupt after each step
                def should_stop():
                    return self.fetchingInterrupted
                
                update_ui("Getting Shazam songs...")
                if not should_stop():
                    getShazamTopSongsWrapper(self, max_rank)
                
                # Get selected chart
                if not should_stop():
                    update_ui(f"Getting songs from {selected_chart}...")
                    getSongsFromBillboard(self, selected_chart, max_rank)
            
            # Final update with success message
            if self.fetchingInterrupted:
                self.after(0, lambda: self.update_progress_message("Fetching stopped. Saving found songs..."))
            else:
                self.after(0, lambda: self.update_progress_message("Finished! Refreshing song list..."))
        
        finally:
            # Update UI in the main thread when done
            self.after(0, self.hide_progress_indicator)
            self.after(0, self.refresh_song_data)

    def interrupt_fetching(self):
        """Interrupt the current fetching process but save what was found"""
        self.fetchingInterrupted = True
        self.stopButton.configure(text="Stopping...", state="disabled")
        self.update_progress_message("Stopping and saving data...")
        self.update()

    def load_playlist_id(self):
        """Load playlist ID from config file"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('youtube_playlist_id', '')
            return ''
        except Exception as e:
            print(f"Error loading config: {e}")
            return ''

def openYoutubeLink(app, pSongID, songsToPlay=None, open_in_browser=False):
    def callback():
        app.update_console("Starting YouTube process...")
        # Use app's songsToPlay property if songsToPlay parameter is None
        actual_songs_to_play = songsToPlay if songsToPlay is not None else app.songsToPlay
        songList = list(range(pSongID, min(pSongID + actual_songs_to_play, len(app.songsNotListened))))
        
        app.update_console(f"Number of songs to process: {len(songList)}")
        
        if not open_in_browser:
            app.update_console(f"YouTube API initialized: {app.youtube is not None}")
            app.update_console(f"Playlist ID: {app.playlist_id}")

        ensure_csv_files_exist()
        with open(fileSongsListened, 'a') as fileListened, open(fileSongsNotListened, 'w') as fileNotListened:
            # Keep track of successfully processed songs
            successfully_processed = set()
            
            for songID in songList:
                song = app.songsNotListened[songID]
                app.update_console(f"\nProcessing song: {song['artist']} - {song['songName']}")
                
                if open_in_browser:
                    # Open in browser
                    webbrowser.open(song['urlYoutube'])
                    app.update_console(f"Opened {song['artist']} - {song['songName']} in browser")
                    successfully_processed.add(songID)
                else:
                    # Add to playlist
                    video_id = app.search_video(f"{song['artist']} - {song['songName']}")
                    app.update_console(f"Video ID found: {video_id}")
                    if video_id and app.playlist_id:
                        if app.add_to_playlist(video_id):
                            app.update_console(f"Added {song['artist']} - {song['songName']} to playlist")
                            successfully_processed.add(songID)
                        else:
                            app.update_console(f"Failed to add {song['artist']} - {song['songName']} to playlist")
                    else:
                        app.update_console(f"Could not add song - Video ID: {video_id}, Playlist ID: {app.playlist_id}")

            id = -1
            fileNotListened.write(headerFile + "\n")
            for song in app.songsNotListened:
                id += 1
                listened = id in successfully_processed

                if not listened:
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
    # Prevent starting new fetching if already in progress
    if self.isLoading:
        print("Song fetching already in progress")
        return
        
    # Show loading indicator if it's a direct call
    self.show_progress_indicator("Fetching songs...")
    
    # Run in a thread
    worker_thread = threading.Thread(
        target=_getSongsFromWWW_thread,
        args=(self, maxRank)
    )
    worker_thread.daemon = True
    worker_thread.start()

def _getSongsFromWWW_thread(self, maxRank):
    try:
        if PRINT_CHART_STATISTICS:
            open(fileChartCount, 'w').close()  # erase count of charts' length
        
        # Update UI using a function to avoid lambda capture issues
        def update_ui(message):
            self.after(0, lambda: self.update_progress_message(message))
        
        # Check if we should interrupt after each step
        def should_stop():
            return self.fetchingInterrupted
        
        update_ui("Getting Shazam songs...")
        if not should_stop():
            getShazamTopSongsWrapper(self, maxRank)
        
        total_charts = len(self.countries)
        for i, chart in enumerate(self.countries):
            if should_stop():
                update_ui("Interrupted! Saving found songs...")
                break
                
            progress_msg = f"Getting songs from {chart} ({i+1}/{total_charts})"
            update_ui(progress_msg)
            getSongsFromBillboard(self, chart, maxRank)
        
        # Final update with success message
        if self.fetchingInterrupted:
            self.after(0, lambda: self.update_progress_message("Fetching stopped. Saving found songs..."))
        else:
            self.after(0, lambda: self.update_progress_message("Finished! Refreshing song list..."))
    finally:
        # Update UI in the main thread when done
        self.after(0, self.hide_progress_indicator)
        self.after(0, self.refresh_song_data)


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
            self.update_console(f"Attribute Error: {e}")
        except Exception as e:
            self.update_console(f"{e}")

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
            
        if criterion == 'rank':
            # Convert rank to integer for proper numerical sorting
            app.songsNotListened.sort(key=lambda x: int(x[criterion]), reverse=isSortReversed)
        else:
            app.songsNotListened.sort(key=lambda x: x[criterion], reverse=isSortReversed)
            
        app.populateSongs()

    return callback()


# def getImageFromChart(chart):
#     # Use the cached image function from auxiliary.py
#     return get_cached_image(chart)


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
        app.update_console("No duplicates")
    else:
        for song in duplicates:
            app.update_console(f"{song['artist']} - {song['songName']}")


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
    
    # Create a CSV file for statistics
    stats_file = "statistics.csv"
    with open(stats_file, 'w') as f:
        f.write("Date,Count\n")
        for date, count in dates.items():
            f.write(f"{date},{count}\n")
    
    app.update_console(f"Statistics written to {stats_file}")


def updateSongDatabase(self, rank, chart, maxRank, stringToAddToNotListened, songsFound):
    if rank == 0:
        self.update_console(f"No songs found in the chart {chart}")
    else:
        if VERBOSE:
            self.update_console(f"Found {str(songsFound): <2} new songs from the {str(maxRank): <2} songs from {chart}")
        else:
            self.update_console(f"Found {str(songsFound): <2}/{str(maxRank): <2} songs from {chart}")
        if PRINT_CHART_STATISTICS:
            with open(fileChartCount, 'a') as f:
                f.write(chart + ";" + str(rank) + ";\n")
    ensure_csv_files_exist()
    with open(fileSongsNotListened, 'a') as fileNotListened:
        fileNotListened.write(stringToAddToNotListened)


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