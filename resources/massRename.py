import os
import re


# Loop through the files in the folder
for originalName in os.listdir(r'.'):
    # print(filename)
    if re.match(".*png", originalName):
        newName = originalName
        newName = re.sub(r'^\d+_', '', newName)
        newName = re.sub(r'flag_', '', newName)
        newName = re.sub(r'_flag', '', newName)
        newName = re.sub(r'_', '-', newName)

        os.rename(originalName, newName)
       
