import setuptools

setuptools.setup(name='youtube_uploader',
      packages=setuptools.find_packages(),
      install_requirements=[
        "google_api_python_client",
        "google_auth_oauthlib",
        "httplib2"
      ],
      version='1.0',
      description='Upload a video to YouTube',
      author='CodingVibe',
      url='https://github.com/codingvibe/youtube-uploader'
     )