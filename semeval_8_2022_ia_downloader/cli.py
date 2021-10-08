"""Console script for semeval_8_2022_ia_downloader."""
import argparse
import json
import os
import os.path
import pathlib
import sys
import time
from urllib.parse import urlparse

import pandas as pd
import requests
from newspaper import Article, Config
from requests import HTTPError, RequestException

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

RESOLVE_FQDN_LIST = ['feedproxy.google.com']


def get_local_path_for_article(article_id, dump_dir):
    dirname = article_id[-2:]
    filename = f'{article_id}.html'
    filepath = os.path.join(dump_dir, dirname, filename)
    return filepath


def parse_input(location):
    df = pd.read_csv(location, index_col='pair_id', encoding='utf8')

    df.rename(columns={"url1_lang": "lang1", "url2_lang": "lang2"}, inplace=True)  # patch for different release format
    all_links = set(df.link1.unique())
    all_links.update(set(df.link2.unique()))
    for pair_id, row in df.iterrows():
        for article_id, article_link, article_lang in zip(pair_id.split('_'),
                                                          row[['link1', 'link2']].values,
                                                          row[['lang1', 'lang2']].values, ):
            domain = urlparse(article_link).netloc
            if domain in RESOLVE_FQDN_LIST:
                # resolve link if e.g., coming from news aggregators like feedproxy.google.com
                try:
                    r = requests.head(article_link, allow_redirects=True)
                    article_link = r.url
                except (TimeoutError, RequestException) as e:
                    print(e)
                    continue
            yield article_id, article_link, article_lang


def get_remaining_articles(location, dump_dir):
    for article_id, article_link, article_lang in parse_input(location):
        filepath = get_local_path_for_article(article_id, dump_dir)
        if not os.path.exists(filepath):
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

    parser.add_argument("--retry", action="store", default="original",
                        help="""when articles are inaccessible from the IA, do:
                        - "original": try downloading from the original source URL
                        - "ignore": do nothing
                        - "log": log inaccessible articles to file
                        """,
                        required=False)
    parser.add_argument("--retry_log", action="store",
                        default="inaccessible_urls_{}.csv".format(time.strftime('%Y%m%d%H%M%S')),
                        help="""path to the file to log inaccessible articles if --retry=log, or if
                        --retry=original and the article is inaccessible also from the original source""",
                        required=False)
    parser.add_argument("--retry_delay", action="store", default=3, type=int,
                        help="how many seconds to wait in between requests if --retry=original",
                        required=False)

    parser.add_argument("--log_level", action="store", default="INFO", help="scrapy log verbosity level",
                        required=False)
    parser.add_argument("--concurrent_requests", action="store", default=1, type=int,
                        help="number of requests sent to the IA at one time",
                        required=False)
    parser.add_argument("--download_delay", action="store", default=1, type=int,
                        help="download delay between requests to the IA",
                        required=False)

    parser.add_argument("--user_agent", action="store",
                        default='semeval_8_2022_ia_downloader (+http://www.euagendas.org/semeval2022)',
                        type=str,
                        help="user agent to identify the script with the IA and original source website",
                        required=False)

    args = parser.parse_args()
    retry_strategy = args.retry
    retry_wait = args.retry_delay
    retry_log = args.retry_log
    headers = {'User-Agent': args.user_agent}
    timeout = 60  # how long to wait for requests when scraping from the original source

    pathlib.Path(args.dump_dir).mkdir(parents=True, exist_ok=True)

    # The path seen from root, ie. from main.py
    settings_file_path = 'semeval_8_2022_ia_downloader.semeval_8_2022_ia_downloader.settings'
    os.environ.setdefault('SCRAPY_SETTINGS_MODULE', settings_file_path)
    scrapy_settings = get_project_settings()
    scrapy_settings.set('LOG_LEVEL', args.log_level)
    scrapy_settings.set('CONCURRENT_REQUESTS', args.concurrent_requests)
    scrapy_settings.set('DOWNLOAD_DELAY', args.download_delay)
    scrapy_settings.set('USER_AGENT', args.user_agent)

    process = CrawlerProcess(scrapy_settings)

    process.crawl('IaArticle', links_file=args.links_file,
                  dump_dir=args.dump_dir)
    process.start()  # the script will block here until the crawling is finished

    # terminate here if there is no wish to attempt re-downloading missing articles
    if retry_strategy == 'ignore':
        pass
    elif retry_strategy == 'original':
        wayback_prefix = 'https://web.archive.org/web/'
        # otherwise, try logging or downloading articles again
        print('downloading inaccessible articles')
        for article_id, article_link, article_lang in get_remaining_articles(args.links_file, args.dump_dir):
            try:
                print('rescraping', article_link)
                # try scraping from wayback
                wayback_link = wayback_prefix + article_link
                wayback_success = False
                try:
                    response = requests.get(wayback_link, headers=headers, allow_redirects=True, timeout=timeout)
                    wayback_success = response.status_code == 200
                    if not wayback_success:
                        print('received a', response.status_code, 'status code from wayback')
                except Exception as e:
                    print(e)
                    print('cannot download from wayback url', wayback_link)
                if not wayback_success:
                    print('rescraping', article_link, 'from the original source')
                    response = requests.get(article_link, headers=headers, allow_redirects=True, timeout=timeout)
                    if response.status_code != 200:
                        print('received a', response.status_code, 'status code from the original source')
                        with open(retry_log, 'a+', encoding='utf-8') as f:
                            f.write(article_link + '\n')
                else:
                    parse_article(args.dump_dir, article_id, article_link, article_lang, html=response.content)
            except Exception as e:
                print(e)
                print('cannot download', article_link)
                with open(retry_log, 'a+', encoding='utf-8') as f:
                    f.write(article_link + '\n')
            time.sleep(retry_wait)
    elif retry_strategy == 'log':
        print('logging inaccessible articles to', retry_log)
        remaining_links = [article_link
                           for _, article_link, _ in get_remaining_articles(args.links_file, args.dump_dir)]
        with open(retry_log, 'a+', encoding='utf-8') as f:
            f.write('\n'.join(remaining_links))
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
