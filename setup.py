#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ ]

test_requirements = [ ]

setup(
    author="Mattia Samory",
    author_email='mattia.samory@gesis.org',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Script that scrapes news articles in the 2021 Semeval Task 8 format from the Internet Archive",
    entry_points={
        'console_scripts': [
            'semeval_8_2021_ia_downloader=semeval_8_2021_ia_downloader.cli:main',
        ],
    },
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='semeval_8_2021_ia_downloader',
    name='semeval_8_2021_ia_downloader',
    packages=find_packages(include=['semeval_8_2021_ia_downloader', 'semeval_8_2021_ia_downloader.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/hide-ous/semeval_8_2021_ia_downloader',
    version='0.1.0',
    zip_safe=False,
)
