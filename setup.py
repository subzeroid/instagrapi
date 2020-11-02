# import pathlib
# import pkg_resources

from setuptools import setup, find_packages

# install_requires = []
# with pathlib.Path('requirements.txt').open() as requirements_txt:
#     install_requires = [
#         str(requirement)
#         for requirement
#         in pkg_resources.parse_requirements(requirements_txt)
#     ]

long_description = '''
Fast and effective Instagram Private API wrapper (public+private requests and challenge resolver)
'''
# with pathlib.Path('README.md').open() as readme_md:
#     long_description = readme_md.read()


setup(
    name='instagrapi',
    version='1.2.1',
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
    description='Fast and effective Instagram Private API wrapper',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    python_requires=">=3.6",
    package_data={'': ["requirements.txt"]},
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
