from shazamio import GenreMusic

VERBOSE = False
IS_AFFECTED_BY_RATING = True
PRINT_CHART_STATISTICS = False

urlSongCharts = "https://www.billboard.com/h/top-music-hits-world-international-song-charts/"
URL_LAST_FM_CHARTS = "https://www.last.fm/charts"
LAST_FM_SONG_TR_CLASS = "js-link-block globalchart-item"

debugging = False
prefix = "_internal/src/" if False else "src/"
fileNameChartLinks = prefix + 'chartsBillboard.csv'
fileSongsListened = prefix + "songsListened.csv"
fileSongsNotListened = prefix + "songsNotListened.csv"
fileChartProperties = prefix + "chartProperties.csv"
fileChartCount = prefix + "chartSongCount.csv"
headerFile = "artist;songName;rank;chart;date;urlYoutube"
headerGUI = ['Artist', 'Song Name', 'Chart', 'Rank', 'Play on Youtube']
columnWidths = [150, 150, 50, 50, 50, 150, 0, 0, 0, 10]
column_widths2 = columnWidths[:2] + [140, 60] + columnWidths[4:5]
rankList = [1, 5, 10, 15, 20, 25, 30, 40, 50, 100, 200, 500]
maxArtistLength = 20
maxSongLength = 20
MAX_SONG_COMPONENT_SIZE = 25
SCORE_NUMERATOR = 20000
SCORE_DENOMINATOR = 8
SCORE_RATING_INERTIA = 10
MIN_SLEEP_BETWEEN_CHARTS = 3
MAX_SLEEP_BETWEEN_CHARTS = 5
ICON_SIZE = 50
PAGE_SIZE_SONG = 15
NO_SONGS_LAST = 20

CHART_TABLE_OFFSET_ROW = 0
CHART_TABLE_OFFSET_COLUMN = 5
SONG_TABLE_OFFSET_ROW = 3
SONG_TABLE_OFFSET_COLUMN = 0

genresShazam = [GenreMusic.ROCK, GenreMusic.POP, GenreMusic.DANCE, GenreMusic.ALTERNATIVE, GenreMusic.ELECTRONIC]
countryCodesShazam = ['RO', 'PH']

TOOLTIP_ALPHA = 0.75

COMBO_BOX_LIST_NO_SONGS = ["1", "5"]