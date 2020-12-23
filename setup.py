from setuptools import setup, find_packages

long_description = '''
Fast and effective Instagram Private API wrapper (public+private requests and challenge resolver)
'''

setup(
    name='instagrapi',
    version='1.3.1',
    author='Mikhail Andreev',
    author_email='x11org@gmail.com',
    license='MIT',
    url='https://github.com/adw0rd/instagrapi',
    install_requires=[
        'pytz==2020.1',
        'requests==2.24.0',
        'PySocks==1.7.1',
        'moviepy==1.0.3',
        'Pillow==7.2.0',
        'pydantic==1.7.2'
    ],
    # test_requires=[],
    keywords='instagram private api',
    description='Fast and effective Instagram Private API wrapper',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    python_requires=">=3.6",
    package_data={'': ["requirements.txt"]},
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ]
)
