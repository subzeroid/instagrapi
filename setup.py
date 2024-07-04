from setuptools import find_packages, setup

long_description = """
Fast and effective Instagram Private API wrapper (public+private requests and challenge resolver).

Use the most recent version of the API from Instagram.

Features:

1. Performs Public API (web, anonymous) or Private API (mobile app, authorized)
   requests depending on the situation (to avoid Instagram limits)
2. Challenge Resolver have Email (as well as recipes for automating receive a code from email) and SMS handlers
3. Support upload a Photo, Video, IGTV, Clips (Reels), Albums and Stories
4. Support work with User, Media, Insights, Collections, Location (Place), Hashtag and Direct objects
5. Like, Follow, Edit account (Bio) and much more else
6. Insights by account, posts and stories
7. Build stories with custom background, font animation, swipe up link and mention users
8. In the next release, account registration and captcha passing will appear
"""

requirements = [
    "requests<3.0,>=2.25.1",
    "PySocks==1.7.1",
    "pydantic==2.8.2",
    "pycryptodomex==3.20.0",
]
# requirements = [
#     line.strip()
#     for line in open('requirements.txt').readlines()
# ]

setup(
    name="instagrapi",
    version="2.1.2",
    author="Mark Subzeroid",
    author_email="143403577+subzeroid@users.noreply.github.com",
    license="MIT",
    url="https://github.com/subzeroid/instagrapi",
    install_requires=requirements,
    keywords=[
        "instagram private api",
        "instagram-private-api",
        "instagram api",
        "instagram-api",
        "instagram",
        "instagram-scraper",
        "instagram-client",
        "instagram-stories",
        "instagram-feed",
        "instagram-reels",
        "instagram-insights",
        "downloader",
        "uploader",
        "videos",
        "photos",
        "albums",
        "igtv",
        "reels",
        "stories",
        "pictures",
        "instagram-user-photos",
        "instagram-photos",
        "instagram-metadata",
        "instagram-downloader",
        "instagram-uploader",
        "instagram-note",
    ],
    description="Fast and effective Instagram Private API wrapper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.9",
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
