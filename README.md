# NM-harvester
Tool for downloading scanned article pages from the internal database of the Nordic Museum
and collating them into djvu files.

Usage:
```
python3 download_articles.py --list list.txt
```
Where `list.txt` contains a list of article UUID's, one per line.

## Authorization
The Dokumentlager API requires authorization.

The script expects to find a `config.py` file in the following format in the working directory.
```
username = "xxxx"
password = "yyyy"
```