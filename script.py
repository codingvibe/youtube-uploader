#!/usr/bin/python

import argparse
import datetime
import errno
import http.client
import httplib2
import json
import os
import random
import sys
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# https://developers.google.com/youtube/v3/guides/uploading_a_video
# https://github.com/googleapis/google-api-python-client/blob/main/docs/oauth.md


# example command
# python upload_video.py --file="/tmp/test_video_file.flv"
#                       --title="Summer vacation in California"
#                       --description="Had fun surfing in Santa Cruz"
#                       --keywords="surfing,Santa Cruz"
#                       --category="22"
#                       --privacy-status="private"


# Requirements
# - auto upload with title, description, keywords, category, and privacy status
# - scheduled public?
# - retries automatically if fails


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
  http.client.IncompleteRead, http.client.ImproperConnectionState,
  http.client.CannotSendRequest, http.client.CannotSendHeader,
  http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The args.client_secrets_file variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google API Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets


# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def valid_date(s):
  try:
    return datetime.date.fromisoformat(s)
  except ValueError:
    msg = "not a valid date: {0!r}".format(s)
    raise argparse.ArgumentTypeError(msg)


def valid_time(s):
  try:
    return datetime.time.fromisoformat(s)
  except ValueError:
    msg = "not a valid time: {0!r}".format(s)
    raise argparse.ArgumentTypeError(msg)


def get_authenticated_service(client_secrets_file):
  flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file,
    scopes=[YOUTUBE_UPLOAD_SCOPE])

  flow.run_local_server()
  credentials = flow.credentials

  return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)


def initialize_upload(youtube, file, title, description,
                      category, keywords, privacy_status, publish_at):
  tags = None
  if keywords:
    tags = keywords.split(",")

  body=dict(
    snippet=dict(
      title=title,
      description=description,
      tags=tags,
      categoryId=category
    ),
    status=dict(
      privacyStatus=privacy_status if publish_at is not None else "private",
      publishAt=publish_at.isoformat()
    )
  )

  print(body)

  # Call the API's videos.insert method to create and upload the video.
  insert_request = youtube.videos().insert(
    part=",".join(list(body.keys())),
    body=body,
    # The chunksize parameter specifies the size of each chunk of data, in
    # bytes, that will be uploaded at a time. Set a higher value for
    # reliable connections as fewer chunks lead to faster uploads. Set a lower
    # value for better recovery on less reliable connections.
    #
    # Setting "chunksize" equal to -1 in the code below means that the entire
    # file will be uploaded in a single HTTP request. (If the upload fails,
    # it will still be retried where it left off.) This is usually a best
    # practice, but if you're using Python older than 2.6 or if you're
    # running on App Engine, you should set the chunksize to something like
    # 1024 * 1024 (1 megabyte).
    media_body=MediaFileUpload(file, chunksize=-1, resumable=True)
  )

  resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
  response = None
  error = None
  retry = 0
  while response is None:
    try:
      print("Uploading file...")
      status, response = insert_request.next_chunk()
      if response is not None:
        if 'id' in response:
          print(("Video id '%s' was successfully uploaded." % response['id']))
        else:
          exit("The upload failed with an unexpected response: %s" % response)
    except HttpError as e:
      if e.resp.status in RETRIABLE_STATUS_CODES:
        error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                             e.content)
      else:
        raise
    except RETRIABLE_EXCEPTIONS as e:
      error = "A retriable error occurred: %s" % e

    if error is not None:
      print(error)
      retry += 1
      if retry > MAX_RETRIES:
        exit("No longer attempting to retry.")

      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      print(("Sleeping %f seconds and then retrying..." % sleep_seconds))
      time.sleep(sleep_seconds)

# TODO: see about getting app verified
def main():
  parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, add_help=True)
  parser.add_argument("--file", required=True, help="Video file to upload")
  parser.add_argument("--title", help="Video title", default="Test Title")
  parser.add_argument("--description", help="Video description",
    default="Test Description")
  parser.add_argument("--category", default="22",
    help="Numeric video category. " +
      "See https://developers.google.com/youtube/v3/docs/videoCategories/list")
  parser.add_argument("--keywords", help="Video keywords, comma separated",
    default="")
  parser.add_argument("--privacy-status", choices=VALID_PRIVACY_STATUSES,
    default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
  parser.add_argument("--publish-at-date", type=valid_date, default=None,
                      help="Date to publish video (format is YYYY-MM-DD)", required=False)
  parser.add_argument("--publish-at-time", type=valid_time, default=None,
                      help="Date to publish video (format is YYYY-MM-DD)", required=False)
  parser.add_argument("--client-secrets-file", help="Path to client secrets json file",
                      default="youtube-uploader-client-credentials.json", required=False)
  args = parser.parse_args()

  # Make sure the upload file exists
  if not os.path.exists(args.file):
    exit("Please specify a valid file using the --file= parameter.")

  # Compile the publish time if applicable
  if (args.publish_at_date is not None and args.publish_at_time is None) or \
     (args.publish_at_date is None and args.publish_at_time is not None):
     exit("Must specify both publish_at date and time for scheduling")

  if args.publish_at_date is not None:
    publish_at = datetime.datetime.combine(args.publish_at_date, args.publish_at_time)

  youtube = get_authenticated_service(args.client_secrets_file)
  try:
    initialize_upload(youtube, args.file, args.title, args.description,
                      args.category, args.keywords, args.privacy_status, publish_at)
  except HttpError as e:
    print(("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)))


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    # The user asked the program to exit
    sys.exit(1)
  except IOError as e:
    # When this program is used in a shell pipeline and an earlier program in
    # the pipeline is terminated, we'll receive an EPIPE error.  This is normal
    # and just an indication that we should exit after processing whatever
    # input we've received -- we don't consume standard input so we can just
    # exit cleanly in that case.
    if e.errno != errno.EPIPE:
      raise

    # We still exit with a non-zero exit code though in order to propagate the
    # error code of the earlier process that was terminated.
    sys.exit(1)

  sys.exit(0)