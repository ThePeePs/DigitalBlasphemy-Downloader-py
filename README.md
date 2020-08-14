# Digital Blasphemy Auto Downloader - Python Edition
This python script will read the json urls from the Android app and auto download user selected sizes of Ryan Bliss's latest renders.
**You must be a Member of Digital Blasphemy** to download the Hi-Res versions (member-sizes).<br>
If you have any suggestions, feature requests or find a bug, please open a issue.<br>
If you would like to contribute, please fork the repo, and submit a Pull Request.

## Requirements
* Python 3.6 or greater
* pipenv
* requests
* pyaml

The script needs to be run from it's directory, or it will not be able to find the config file.

## Installation
### Windows Install

(Please note, I do not have a Windows computer to test this on. If you can write better install/setup directions, please let me know.)

Download Python for Windows and install.<br>
* [Python for 64 bit Windows](https://www.python.org/ftp/python/3.7.6/python-3.7.6-amd64.exe)
* [Python for 32 bit Windows](https://www.python.org/ftp/python/3.7.6/python-3.7.6.exe)


Download Git client for windows at: https://desktop.github.com/ and install

Open the "Git Shell" and paste the following:

    git clone https://github.com/ThePeePs/DigitalBlasphemy-Downloader.git db-downloader

Open a cmd prompt and set up the python virtual environment. (copy/paste below)
    
    cd db-downloader
    pipenv update

Copy or rename `config.yaml.default` to `config.yaml`.<br>
Edit the config (`config.yaml`) to suit your needs. (I suggest using Wordpad or [Notepad++](https://notepad-plus-plus.org/downloads/ "Notepad++ Website"))

To run the script. open a command prompt, and cd to the directory of the script, and enter:

    pipenv run python db-downloader.py

I suggest you set it up as a scheduled task to run at least once a week.

### Linux and MacOS Install

Clone the repo.

    git clone https://github.com/ThPeePs/DigitalBlasphemy-Downloader.git db-downloader

Pip install requests and pyYAML

    cd DigitalBlasphmey-Downloader db-downloader
    pipenv sync
    
Copy or rename `config.yaml.default` to `config.yaml`.<br>
Edit the config (`config.yaml`) to suit your needs.

Then run the script from it's directory.

    pipenv run python db-downloader.py

I suggest you set it up as a cron job to run at least once a week.

### TODO
* cleanup href's for text version of email
* add option to sort by gallery as well as by size
