import os.path
from setuptools import setup, find_packages

base = os.path.abspath(os.path.dirname(__file__))

setup(
    name='instagrapi',
    version='1.0.8',
    author='Mikhail Andreev',
    author_email='x11org@gmail.com',
    license='MIT',
    url='https://github.com/adw0rd/instagrapi',
    install_requires=[
        'pytz>=2020.1',
        'requests>=2.24.0',
        'moviepy>=1.0.3',
        'Pillow>=7.2.0'
    ],
    # test_requires=[],
    keywords='instagram private api',
    description='Fast and effective Instagram Private API wrapper (public+private requests and challenge resolver)',
    long_description=open(os.path.join(base, 'README.md')).read(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    python_requires=">=3",
    package_data={'': ["requirements.txt"]},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3',
    ],
)
