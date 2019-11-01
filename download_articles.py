#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Download articles from Dokumentlager.

Given a list of uuid's, download
image files from Dokumentlager and
collate them into Commons-ready
djvu files.
"""
import argparse
import json
import os
import time
from shutil import which  # used for djvu conversion
from subprocess import run  # used for djvu conversion
from tqdm import tqdm
import requests

import config


def create_directory(dirname):
    """
    Create directory with given name.

    @param dirname: name of directory
    @type dirname: string
    """
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    return dirname


def file_to_list(filename):
    """
    Read lines of text file to a list.

    @param filename: path to file
    @type filename: string
    @return list of lines
    """
    with open(filename) as fil:
        meat = fil.readlines()
        return [i.strip() for i in meat]


def generate_url(internal_id):
    """
    Generate url of article in Dokumentlager.

    @param internal_id: uuid of article
    @type internal_id: string
    @return url to get all data of one article
    """
    template = "https://dokumentlager.nordiskamuseet.se/api/list/{}/0/500"
    return template.format(internal_id)


def get_image_paths(article_data):
    """
    Get paths of all images belonging to article.

    Process the API response containing all
    data of an article, extracting paths of
    the scanned pages.

    @param article_data: raw API response
    @type article_data: string
    """
    file_url = "http://dokumentlager.nordiskamuseet.se/"\
        "binaryDownload/{}?profile={}&mimeType={}"
    paths = []
    article_data = json.loads(article_data)
    resources = [x for x in article_data if x["entityType"] == "Resource"]
    files = [x["properties"]["resource.originalFile"] for x in resources]
    for fil in files:
        images = [x for x in fil if x["value"]["mimeType"] == "image/tiff"]
        reference = [x["value"]["reference"] for x in images][0]
        mimetype = [x["value"]["mimeType"] for x in images][0]
        profile = [x["value"]["profile"] for x in images][0]
        filename = [x["value"]["originalFileName"] for x in images][0]
        url = file_url.format(reference, profile, mimetype)
        paths.append({"filename": filename, "url": url})
    return paths


def download_images(url_list, internal_id):
    """
    Download all images in a url list.

    The files are saved in a directory
    named with the uuid of the article.

    @param url_list: dict of files, in format
                     {"filename" : "x.tiff", "url" : "y"}
    @type url_list: dict
    @param internal_id: uuid of article
    @type internal_id: string
    """
    target_dir = create_directory(internal_id)
    for url in url_list:
        path = os.path.join(target_dir, url["filename"])
        print(url)
        img_data = requests.get(url["url"]).content
        with open(path, 'wb') as handler:
            handler.write(img_data)


def download_files_of_article(internal_id):
    """
    Download all img files of an article.

    @param internal_id: uuid of article
    @type itnernal_id: string
    """
    print("Downloading files of {}".format(internal_id))
    url = generate_url(internal_id)
    auth = (config.username, config.password)
    response = requests.get(url, auth=auth)
    article_images = get_image_paths(response.text)
    download_images(article_images, internal_id)


def create_djvu(dirname):
    """
    Create djvu files from images in a directory.

    The djvu file has the same name as the
    directory with image files.
    @param dirname: name of directory with images
    @type dirname: string
    """
    target_dir = create_directory("output")
    tmp_djvu = "tmp.djvu"
    book_djvu = os.path.join(target_dir, "{}.djvu".format(dirname))
    files = sorted([x for x in os.listdir(dirname) if x.endswith(".tif")])
    for i, page in tqdm(enumerate(files, 1), total=len(files)):
        run(['cjb2', '-clean', os.path.join(dirname, page),
             tmp_djvu], check=True)
        if i == 1:
            run(['djvm', '-c', book_djvu, tmp_djvu], check=True)
        else:
            run(['djvm', '-i', book_djvu, tmp_djvu], check=True)
    os.remove(tmp_djvu)


def start_error_log():
    """Create timestamped filename for error log."""
    tstamp = time.strftime("%Y%m%d-%H%M%S")
    return "{}.log".format(tstamp)


def log_weird_article(internal_id, error_log):
    """
    Save uuid of article that looks wrong.

    Some articles in Dokumentlager seem to be
    missing image files for some of the
    pages. This manifests itself by xml files
    not containing links to equivalent image,
    causing get_image_paths to error out.

    @param internal_id: uuid of article
    @type internal_id: string
    @param error_log: filename of error log
    @type error_log: string
    """
    with open(error_log, "a") as error_file:
        error_file.write("{}\n".format(internal_id))


def main(arguments):
    """Load list of uuid's and create djvu's."""
    error_log = start_error_log()
    ids = file_to_list((arguments.get("list")))
    print("Loaded {} internal ID's.".format(len(ids)))
    for int_id in ids:
        try:
            download_files_of_article(int_id)
        except IndexError:
            log_weird_article(int_id, error_log)
            continue
        create_djvu(int_id)


def can_djvu():
    """
    Check if DjVu files can be created.

    Check whether DjVuLibre is installed,
    on PATH and marked as executable.
    """
    return which('djvm') is not None and which('cjb2') is not None


if __name__ == "__main__":
    if not can_djvu():
        raise Exception('Djvu utils djvm and cjb2 not found.')
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("--list", required=True)
    ARGS = PARSER.parse_args()
    main(vars(ARGS))
