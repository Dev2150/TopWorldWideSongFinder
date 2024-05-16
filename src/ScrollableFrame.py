import functools
import webbrowser

import customtkinter as ctk

from src.globalVariables import headerGUI


class tableSongs(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.populateTable(master)

    def populateTable(self, master):
        for songID in range(master.pageSongNotListened * master.stepSizeSong,
                            min((master.pageSongNotListened + 1) * master.stepSizeSong, len(master.songsNotListened))):
            song = master.songsNotListened[songID]
            if songID == 0:
                continue

            for col, header in enumerate(headerGUI):
                label = ctk.CTkLabel(self, text=header, padx=10, pady=5, fg_color="gray")
                label.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")

            lblArtist = ctk.CTkLabel(master=self, text=song['artist'], justify=ctk.RIGHT)
            lblArtist.grid(row=songID, column=0)

            lblSongName = ctk.CTkLabel(master=self, text=song['songName'], justify=ctk.RIGHT)
            lblSongName.grid(row=songID, column=1)

            lblChart = ctk.CTkLabel(master=self, text=song['chart'], justify=ctk.RIGHT)
            lblChart.grid(row=songID, column=2)

            lblRank = ctk.CTkLabel(master=self, text=song['rank'], justify=ctk.RIGHT)
            lblRank.grid(row=songID, column=3)

            btnListen = ctk.CTkButton(master=self, text="Listen", fg_color="red",
                                      command=functools.partial(openYoutubeLink, songID, master))
            btnListen.grid(row=songID, column=4)


def openYoutubeLink(songID, app):
    def callback():
        webbrowser.open(app.songsNotListened[songID]['urlYoutube'])
        app.songsNotListened.remove(songID)

    return callback()
