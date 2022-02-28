# youtube-uploader
Updated version of the Python YouTube upload example from Google with extra command line arguments.

## Install Requirements

`pip install`

## Run the script

`python youtube_uploader.py <arguments>`

### Command line arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| --file | path to video file to upload | true | N/A |
| --title | title of the uploaded video | false | Test Title |
| --description | description of the video | false | Test Description |
| --category | YouTube category of video (https://developers.google.com/youtube/v3/docs/videoCategories/list) | false | 22 |
| --keywords | comma separated list of tags | false | |
| --privacy-status | privacy status of video | false | public |
| --publish-at-date | date to publish video (format is YYYY-MM-DD) | false | |
| --publish-at-time | time to publish video (iso format) | false | |
| --client-secrets-file | path to client secrets json file | false | `youtube-uploader-client-credentials.json` |