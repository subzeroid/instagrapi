import os

from setuptools import find_packages, setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='mkdocs-redirects_relative_redirects',
    version='1.0.1.b1',
    description='A MkDocs plugin for dynamic page redirects to prevent broken links.',
    python_requires='>=2.7',
    install_requires=[
        'mkdocs>=1.0.4',
    ],
    extras_require={
        'release': [
            'twine==1.13.0',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
    packages=find_packages(),
    entry_points={
        'mkdocs.plugins': [
            'redirects = mkdocs_redirects.plugin:RedirectPlugin'
        ]
    }
)
