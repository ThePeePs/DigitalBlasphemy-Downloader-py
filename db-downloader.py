#!/usr/bin/env python3

# This code is copyrighted under the GPL ver. 3.0 license, which should come with this file.
# Copyright (c) Patrick Palmieri 2020

import re
import os
import errno
import json
import time
import smtplib
import logging
import argparse
from email.message import EmailMessage
from email.headerregistry import Address

import requests
import yaml

__version__ = "0.2"


parser = argparse.ArgumentParser(description=f"DigitalBlasphemy Auto Downloader version {__version__}")
parser.add_argument("-c", "--config", default="config.yaml", help="Path to config file.")
parser.add_argument("-d", "--debug",  default=False, action="store_true", help="Enable debug.")
parser.add_argument("-s", "--console", default=False, action="store_true", help="Log to screen.")
parser.add_argument("-V", "--version", action="version", version=f"db-downloader.py {__version__}",
                    help="Display version")

args = parser.parse_args()

with open(args.config, 'r') as yf:
    config = yaml.full_load(yf)

if args.debug:
    config['logging']['level'] = "DEBUG"
if args.console:
    config['logging']['consolelog'] = True

# Set our data and base directories
data_envvar = re.match(r'.*__(.*)__.*', config['filepath']['datadir']).groups()[0]
base_envvar = re.match(r'.*__(.*)__.*', config['filepath']['basedir']).groups()[0]
basedir = re.sub(r'__.*__', os.environ[base_envvar], config['filepath']['basedir'])
datadir = re.sub(r'__.*__', os.environ[data_envvar], config['filepath']['datadir'])

# Check to see if directories exist, if not make them
if not os.path.exists(basedir):
    try:
        os.makedirs(basedir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print(f"Unable to create basedir path of: {basedir}\nError: {e.strerror} {e.filename}")
        else:
            print(f"Path of: {basedir} already exists.\nError: {e.strerror} {e.filename}")
        raise SystemExit
if not os.path.exists(datadir):
    try:
        os.makedirs(datadir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print(f"Unable to create datadir path of: {basedir}\nError: {e.strerror} {e.filename}")
        else:
            print(f"Path of: {datadir} already exists.\nError: {e}")
        raise SystemExit

# Setup logging
logger = logging.getLogger("db_downloader")
log_format = logging.Formatter("%(asctime)s\t%(levelname)s:\t%(message)s")
logger.setLevel(logging.getLevelName(config['logging']['level']))
if config['logging']['consolelog']:
    clh = logging.StreamHandler()
    clh.setFormatter(log_format)
    logger.addHandler(clh)
flh = logging.FileHandler(os.path.join(datadir, config['logging']['logfile']))
flh.setFormatter(log_format)
logger.addHandler(flh)

# Setup some base variables
db_site = "https://digitalblasphemy.com"

session = requests.Session()
session.auth = (config['dbinfo']['user'], config['dbinfo']['pass'])
session.headers.update({f"User-Agent": f"Mozilla/5.0; ThePeePs auto Downloader v.{__version__}"})

if config['proxy']['use']:
    for server in config['proxy']['servers']:
        p_type = re.match(r'^(http.*:).*', server).groups()[0]
        p_type = re.sub(r':', "", p_type)
        session.proxies.update({p_type: server})
        logger.debug(f"Adding proxy: {server}, type {p_type} to http session")
    else:
        logger.debug("Not using proxy for http session connection.")

login_check = session.get(f"{db_site}/content")
if login_check.status_code != 200:
    logger.error(f"Login Failed: {login_check.reason}")
    session.close()
    logging.shutdown()
    raise SystemExit
else:
    logger.debug("Login to Digital Blasphemy complete.")

galleries = session.get(f"{db_site}/galleries.json")
if galleries.status_code == 200:
    galleries_dict = json.loads(galleries.text)
    logger.debug("Download of Gallery Listing complete.")
else:
    logger.error(f"Unable to fetch galleries.json: {galleries.reason} (HTTP Error: {galleries.status_code})")
    session.close()
    logging.shutdown()
    raise SystemExit


gallery_uri = [gallery['href'] for gallery in galleries_dict if gallery['name'] == "Newest"]
if len(gallery_uri) == 1:
    gallery_uri = gallery_uri[0]
else:
    logger.error("Newest Gallery not found, exiting.")
    raise SystemExit

newest = session.get(f"{db_site}{gallery_uri}")

if newest.status_code == 200:
    newest_dict = json.loads(newest.text)
    logger.debug("Download of Newest Gallery complete.")
else:
    logger.error(f"Unable to fetch Newest Gallery: {newest.reason} (HTTP Error: {newest.status_code})")
    session.close()
    logging.shutdown()
    raise SystemExit

# Go though the gallery, and download the images and sizes we don't have.
dl_list = []
got_new = False
for listing in newest_dict:
    dl_sizes = []
    listing_ret = session.get(f"{db_site}{listing['href']}")
    if listing_ret.status_code == 200:
        listing_data = json.loads(listing_ret.text)
        logger.debug(f"Download of {listing_data['title']} info complete.")

        # Loop though want list
        for grab in config['dlsizes']:
            dl_try = False
            img_path = os.path.join(basedir, grab['path'], f"{listing['id']}.jpg")
            if not os.path.exists(img_path):
                dl_path = os.path.join(basedir, grab['path'])
                if not os.path.exists(dl_path):
                    logger.debug(f"Creating download path {dl_path}.")
                    try:
                        os.makedirs(dl_path)
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            logger.error(f"Unable to create download path of: {dl_path}\n"
                                         f"Error: {e.strerror} {e.filename}")
                        else:
                            logger.error(f"Path of: {dl_path} already exists.\nError: {e.strerror} {e.filename}")
                        logger.warning(f"Skipping download size {listing['title']} of {grab['size']} "
                                       f"due to path creation issues.")
                else:
                    logger.debug(f"Download path {dl_path} exists.")

                # Loop though resolutions that are avail for download.
                for listing_res in listing_data['resolutions']:
                    if grab['size'] == listing_res['title']:
                        dl_try = True
                        image_ret = session.get(f"{db_site}{listing_res['href']}")
                        if image_ret.status_code == 200:
                            if len(image_ret.content) == int(image_ret.headers['content-length']):
                                with open(img_path, "wb") as img:
                                    img.write(image_ret.content)
                                dl_sizes.append({"name": grab['size'], "status": 1})
                                got_new = True
                                logger.info(f"Download size {grab['size']} of {listing['title']} successful")
                            else:
                                logging.warning(f"Download size {grab['size']} of {listing['title']} failed; only got "
                                                f"{len(image_ret.content)} of {image_ret.headers['content-length']}"
                                                f" bytes")
                                dl_sizes.append({'name': grab['size'], 'status': 0})
                        else:
                            logging.warning(f"Download size {grab['size']} of {listing['title']} failed; http error "
                                            f"{image_ret.reason} (error: {image_ret.status_code})")
                            dl_sizes.append({"name": grab['size'], "status": 0})
                        logger.debug("Waiting 2 sec to prevent DoS like downloading.")
                        time.sleep(2)
                if not dl_try:
                    logger.info(f"Download size {grab['size']} of {listing['title']} is not available for download.")
                    dl_sizes.append({"name": grab['size'], "status": 3})

            else:
                logger.info(f"Image size {grab['size']} of {listing['title']} exists, skipping")
                dl_sizes.append({"name": grab['size'], "status": 2})
        dl_list.append({"title": listing['title'], "id": listing['id'], "sizes": dl_sizes,
                        "story": listing_data['story'], "thumbnail": listing_data['preview']})
    else:
        logger.warning(f"Download of {listing['title']} info failed, moving on to next.")

dl_status = ["Failed", "Success", "Previously downloaded", "Not available"]

# Build Body of email (both text and html)
# If console output is enabled, the text version will be printed out to the console.
html_results = "<!DOCTYPE html>\n<html>\n<head></head>\n<body>\n    <h2 align=\"center\">Results of Downloading:</h2>\n"
text_results = "Results of Downloading:\n"

# Loop for each Render
for image in dl_list:
    html_results += f"    <h3 align=\"center\">{image['title']}</h3>\n" \
                    f"   <center><a href=\"{db_site}/preview.shtml?i={image['id']}\">" \
                    f"<img src=\"{db_site}{image['thumbnail']}\" title=\"{image['title']}\"></a></center>\n" \

    text_results += f"Name: {image['title']}\nStory:\n"
    # Loop for story lines
    # TODO cleanup href's for text version of email
    for line in image['story']:
        line = re.sub(r'href="/', f"href=\"{db_site}/", line)
        line = re.sub(r'href="p', f"href=\"{db_site}/p", line)
        html_results += f"    <p>{line}</p>\n"
        text_results += f"{line}\n\n"

    html_results += f"    <table border=\"0\" cellspacing=\"0\" cellpadding=\"5\">\n" \
                    f"      <tr><th>Resolution</th><th>Downloaded Status</th></tr>\n"
    text_results += f"Preview: {db_site}{image['thumbnail']}\n\n    Resolution   Download Status\n"

    # Loop for sizes in Render
    link_color = ["red", "green", "purple", "blue"]
    for size in image['sizes']:
        text_results += f"    {size['name']:>11}: {dl_status[size['status']]}\n"
        html_results += f"      <tr><td>{size['name']}</td><td><font color=\"{link_color[size['status']]}\">" \
                        f"{dl_status[size['status']]}</font></td></tr>\n"
    html_results += "    </table>\n"
    text_results += "\n\n"


html_results += "  </body>\n</html>\n"

# Build email, and send
if config['mail']['send'] and got_new:
    envelope = EmailMessage()
    (from_name, from_user, from_domain) = config['mail']['from'].split(",")
    to_tuple = ()
    for recp in config['mail']['to'].split(":"):
        (to_name, to_user, to_domain) = recp.split(",")
        to_tuple = to_tuple + (Address(to_name, to_user, to_domain),)
    envelope['Subject'] = "New Images downloaded from Digital Blasphemy"
    envelope['From'] = Address(from_name, from_user, from_domain)
    envelope['To'] = to_tuple
    envelope.set_content(text_results)
    envelope.add_alternative(html_results, subtype="html")

    server = smtplib.SMTP(config['mail']['server'], config['mail']['port'])
    server.local_hostname = "db-downloader"
    server.ehlo_or_helo_if_needed()
    if "starttls" in server.esmtp_features:
        server.starttls()
    if config['mail']['auth_req']:
        try:
            server.login(config['mail']['user'], config['mail']['pass'])
        except smtplib.SMTPAuthenticationError as err:
            strerror = re.sub(r'.*Error: ', "", err.smtp_error.decode())
            logger.error(f"SMTP auth failed: {strerror}, Code: {err.smtp_code}")
        except smtplib.SMTPException as err:
            logger.error(f"SMTP auth failed: {err.strerror}, Code: {err.errno}")
    try:
        server_ret = server.send_message(envelope)
        server.quit()
        if len(server_ret) == 0:
            logger.debug("Mail sent successfully")
        else:
            logger.warning(f"Got error from SMTP server, some mail might have not been sent: {server_ret.code}")
    except smtplib.SMTPSenderRefused as err:
        strerror = re.sub(r'.*Error: ', "", err.smtp_error.decode())
        logger.error("Sending mail failed: {0}, Code: {1}".format(strerror, err.smtp_code))
    except smtplib.SMTPDataError as err:
        strerror = re.sub(r'.*Error: ', "", err.smtp_error.decode())
        logger.error("Sending mail failed: {0}, Code: {1}".format(strerror, err.smtp_code))


if config['logging']['consolelog']:
    print(text_results)

logging.shutdown()
session.close()
raise SystemExit
