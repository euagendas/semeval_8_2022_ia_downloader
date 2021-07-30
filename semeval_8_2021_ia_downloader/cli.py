"""Console script for semeval_8_2021_ia_downloader."""
import argparse
import os
import pathlib
import sys

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def main():
    """Console script for semeval_8_2021_ia_downloader."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--dump_dir', action="store", default="output", help='dump folder path', required=False)
    parser.add_argument("--links_file", action="store", default="sample_data.csv", help="File to read",
                        required=False,
                        metavar="INFILE")

    args = parser.parse_args()

    pathlib.Path(args.dump_dir).mkdir(parents=True, exist_ok=True)

    settings_file_path = 'semeval_8_2021_ia_downloader.semeval_8_2021_ia_downloader.settings'  # The path seen from root, ie. from main.py
    os.environ.setdefault('SCRAPY_SETTINGS_MODULE', settings_file_path)
    process = CrawlerProcess(get_project_settings())

    process.crawl('IaArticle', links_file=args.links_file,
                  dump_dir=args.dump_dir)
    process.start()  # the script will block here until the crawling is finished

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
