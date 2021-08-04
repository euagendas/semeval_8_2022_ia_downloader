"""Console script for semeval_8_2022_ia_downloader."""
import argparse
import json
import os
import os.path
import pathlib
import sys
from urllib.parse import urlparse

import pandas as pd
import requests
from newspaper import Article

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


RESOLVE_FQDN_LIST = ['feedproxy.google.com']


def parse_input(location):
    df = pd.read_csv(location, index_col='pair_id')
    all_links = set(df.link1.unique())
    all_links.update(set(df.link2.unique()))
    for pair_id, row in df.iterrows():
        for article_id, article_link, article_lang in zip(pair_id.split('_'),
                                                          row[['link1', 'link2']].values,
                                                          row[['lang1', 'lang2']].values, ):
            domain = urlparse(article_link).netloc
            if domain in RESOLVE_FQDN_LIST:
                # resolve link if e.g., coming from news aggregators like feedproxy.google.com
                r = requests.head(article_link, allow_redirects=True)
                article_link = r.url
            yield article_id, article_link, article_lang


def parse_article(dump_dir, article_id, article_link, article_lang, html=None):
    dirname = article_id[-2:]
    filename = f'{article_id}.html'
    filepath = os.path.join(dump_dir, dirname, filename)
    pathlib.Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)

    article = Article(article_link, language=article_lang)

    if html is None:
        article.download()
        article.html = article.html.encode()
    else:
        # set html manually
        article.html = html
        article.download_state = 2

    with open(filepath, 'wb') as f:
        f.write(article.html)
    article.parse()
    article_dict = dict(source_url=article.source_url,
                        url=article.url,
                        title=article.title,
                        top_image=article.top_image,
                        meta_img=article.meta_img,
                        images=list(article.images),
                        movies=article.movies,
                        text=article.text,
                        keywords=article.keywords,
                        meta_keywords=article.meta_keywords,
                        tags=list(article.tags),
                        authors=article.authors,
                        publish_date=article.publish_date and article.publish_date.ctime() or None,
                        summary=article.summary,
                        article_html=article.article_html,
                        meta_description=article.meta_description,
                        meta_lang=article.meta_lang,
                        meta_favicon=article.meta_favicon,
                        meta_data=dict(article.meta_data),
                        canonical_link=article.canonical_link
                        )

    filename = f'{article_id}.json'
    filepath = os.path.join(dump_dir, dirname, filename)
    with open(filepath, 'w') as f:
        f.write(json.dumps(article_dict))


def main():
    """Console script for semeval_8_2022_ia_downloader."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--dump_dir', action="store", default="articles", help='dump folder path', required=False)
    parser.add_argument("--links_file", action="store", default="sample_data.csv", help="File to read",
                        required=True,
                        metavar="INFILE")

    parser.add_argument("--log_level", action="store", default="INFO", help="scrapy log verbosity level",
                        required=False)
    args = parser.parse_args()

    pathlib.Path(args.dump_dir).mkdir(parents=True, exist_ok=True)

    settings_file_path = 'semeval_8_2022_ia_downloader.semeval_8_2022_ia_downloader.settings'  # The path seen from root, ie. from main.py
    os.environ.setdefault('SCRAPY_SETTINGS_MODULE', settings_file_path)
    scrapy_settings = get_project_settings()
    scrapy_settings.set('LOG_LEVEL', args.log_level)

    process = CrawlerProcess(scrapy_settings)

    process.crawl('IaArticle', links_file=args.links_file,
                  dump_dir=args.dump_dir)
    process.start()  # the script will block here until the crawling is finished

    for article_id, article_link, article_lang in parse_input(args.links_file):
        dirname = article_id[-2:]
        filename = f'{article_id}.html'
        filepath = os.path.join(args.dump_dir, dirname, filename)
        if not os.path.exists(filepath):
            print('rescraping ', article_link)
            parse_article(args.dump_dir, article_id, article_link, article_lang, html=None)

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
