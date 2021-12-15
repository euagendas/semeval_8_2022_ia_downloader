"""Console script for semeval_8_2022_ia_downloader."""
import argparse
import json
import os
import os.path
import pathlib
import sys
import time
from multiprocessing import Pool
from urllib.parse import urlparse, urljoin

import pandas as pd
import requests
import tqdm
from newspaper import Article, Config
from requests import RequestException

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

RESOLVE_FQDN_LIST = ['feedproxy.google.com']


def get_local_path_for_article(article_id, dump_dir, extension='.json'):
    dirname = article_id[-2:]
    filename = article_id + extension
    filepath = os.path.join(dump_dir, dirname, filename)
    return filepath


def parse_input(location):
    df = pd.read_csv(location, index_col='pair_id', encoding='utf8')

    df.rename(columns={"url1_lang": "lang1", "url2_lang": "lang2"}, inplace=True)  # patch for different release format
    all_links = set(df.link1.unique())
    all_links.update(set(df.link2.unique()))

    # https://stackoverflow.com/a/36806159
    # Query parameters are parsed as additional parameters to the API rather than as part of the url

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


def get_remaining_articles(location, dump_dir, min_text_length=0):
    for article_id, article_link, article_lang in parse_input(location):
        filepath = get_local_path_for_article(article_id, dump_dir)
        if not os.path.exists(filepath):
            yield article_id, article_link, article_lang
        else:
            with open(filepath, encoding='utf8') as f:
                article_json = json.loads(f.read())
                if ('text' not in article_json) or (len(article_json['text'].strip()) <= min_text_length):
                    yield article_id, article_link, article_lang


def parse_article(dump_dir, article_id, article_link, article_lang, html=None, article_config=None):
    dirname = article_id[-2:]
    filename = f'{article_id}.html'
    filepath = os.path.join(dump_dir, dirname, filename)
    pathlib.Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)
    article = Article(article_link, language=article_lang, config=article_config)

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


def rescrape_original(args):
    article_id, article_link, article_lang, article_config, dump_dir, retry_wait = args
    try:
        # print('rescraping', article_link)
        parse_article(dump_dir, article_id, article_link, article_lang, html=None,
                      article_config=article_config)
    except Exception as e:
        print(e)
        print('cannot download from', article_link)
    time.sleep(retry_wait)


def rescrape_wayback(args):
    article_id, article_link, article_lang, article_config, dump_dir, retry_wait = args
    try:
        wayback_prefix = 'https://web.archive.org/web/'
        # print('rescraping', article_link)
        wayback_link = wayback_prefix + article_link
        response = requests.head(wayback_link, allow_redirects=True)
        wayback_link = response.url[:42] + 'id_' + response.url[42:]
        # print('translates to', wayback_link)
        rescrape_original((article_id, wayback_link, article_lang, article_config, dump_dir, retry_wait))
    except Exception as e:
        print(e)
        print('cannot download from wayback url', wayback_link)


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
    parser.add_argument("--retry_min_chars", action="store", default=50, type=int,
                        help="retry downloading also articles for which the ",
                        required=False)

    parser.add_argument("--log_level", action="store", default="INFO", help="scrapy log verbosity level",
                        required=False)
    parser.add_argument("--concurrent_requests", action="store", default=1, type=int,
                        help="number of parallel requests",
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
    min_text_length = args.retry_min_chars

    article_config = Config()
    article_config.browser_user_agent = args.user_agent
    article_config.request_timeout = 60

    pathlib.Path(args.dump_dir).mkdir(parents=True, exist_ok=True)

    print('Phase 1: scrape after querying the internet archive\'s CDX server')
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
                  dump_dir=args.dump_dir,
                  min_text_length=args.retry_min_chars
                  )
    process.start()  # the script will block here until the crawling is finished

    if retry_strategy == 'ignore':
        # terminate here if there is no wish to attempt re-downloading missing articles
        pass
    elif retry_strategy == 'original':
        # otherwise, try logging or downloading articles again
        print('Phase 2: rescrape using the internet archive\'s /web/ endpoint')

        # try scraping from wayback
        remaining_articles = list(get_remaining_articles(args.links_file,
                                                         args.dump_dir,
                                                         min_text_length))
        wayback_pool = Pool(processes=args.concurrent_requests)
        for _ in tqdm.tqdm(wayback_pool.imap_unordered(rescrape_wayback, [(article_id,
                                                                           article_link,
                                                                           article_lang,
                                                                           article_config,
                                                                           args.dump_dir,
                                                                           retry_wait) for (article_id,
                                                                                            article_link,
                                                                                            article_lang) in
                                                                          remaining_articles]),
                           desc='downloading inaccessible articles from the web archive',
                           total=len(remaining_articles)):
            pass
        wayback_pool.close()
        wayback_pool.join()

        print('Phase 3: rescrape using the internet archive\'s /web/ endpoint, after stripping url query parameters')
        # try scraping from wayback, stripping query parameters
        remaining_articles = list(map(lambda x: (x[0], urljoin(x[1], urlparse(x[1]).path), x[2]),
                                      filter(lambda x: len(urlparse(x[1]).query) > 0,
                                             get_remaining_articles(args.links_file,
                                                                    args.dump_dir,
                                                                    min_text_length))))
        wayback_noquery_pool = Pool(processes=args.concurrent_requests)
        for _ in tqdm.tqdm(wayback_noquery_pool.imap_unordered(rescrape_wayback, [(article_id,
                                                                                   article_link,
                                                                                   article_lang,
                                                                                   article_config,
                                                                                   args.dump_dir,
                                                                                   retry_wait) for (article_id,
                                                                                                    article_link,
                                                                                                    article_lang) in
                                                                                  remaining_articles]),
                           desc='downloading articles without query parameters from the web archive',
                           total=len(remaining_articles)):
            pass
        wayback_noquery_pool.close()
        wayback_noquery_pool.join()

        # try scraping from the original source
        print('Phase 4: rescrape from the original source')
        remaining_articles = list(get_remaining_articles(args.links_file,
                                                         args.dump_dir,
                                                         min_text_length))
        original_pool = Pool(processes=args.concurrent_requests)
        for _ in tqdm.tqdm(original_pool.imap_unordered(rescrape_original, [(article_id,
                                                                             article_link,
                                                                             article_lang,
                                                                             article_config,
                                                                             args.dump_dir,
                                                                             retry_wait) for (article_id,
                                                                                              article_link,
                                                                                              article_lang) in
                                                                            remaining_articles]),
                           desc='downloading inaccessible articles from the original source',
                           total=len(remaining_articles)):
            pass
        original_pool.close()
        original_pool.join()

        missing_links = [link for _, link, _ in get_remaining_articles(args.links_file, args.dump_dir, 0)]
        with open(retry_log, 'w+', encoding='utf-8') as f:
            f.write('\n'.join(missing_links))

    elif retry_strategy == 'log':
        print('logging inaccessible articles to', retry_log)
        remaining_links = [article_link
                           for _, article_link, _ in get_remaining_articles(args.links_file, args.dump_dir)]
        with open(retry_log, 'a+', encoding='utf-8') as f:
            f.write('\n'.join(remaining_links))
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
