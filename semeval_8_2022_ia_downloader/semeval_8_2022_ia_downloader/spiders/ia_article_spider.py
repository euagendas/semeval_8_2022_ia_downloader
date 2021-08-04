import json
import os.path
import pathlib
from urllib.parse import urlparse

import pandas as pd
import requests
import scrapy
from newspaper import Article
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError

RESOLVE_FQDN_LIST = ['feedproxy.google.com']


class IaArticleSpider(scrapy.Spider):
    name = "IaArticle"

    def start_requests(self):
        df = pd.read_csv(self.links_file, index_col='pair_id')
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
                yield scrapy.Request(article_link,
                                     errback=self.errback_httpbin,
                                     meta={'article_id': article_id,
                                           'article_link': article_link,
                                           'article_lang': article_lang,
                                           })

    def errback_httpbin(self, failure):
        # log all errback failures,
        # in case you want to do something special for some errors,
        # you may need the failure's type
        self.logger.error(repr(failure))
        self.logger.error("in errback")

        # if isinstance(failure.value, HttpError):
        if failure.check(HttpError):
            # you can get the response
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        # elif isinstance(failure.value, DNSLookupError):
        elif failure.check(DNSLookupError):
            # this is the original request
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        # elif isinstance(failure.value, TimeoutError):
        elif failure.check(TimeoutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)

    def parse(self, response):
        article_id = response.meta['article_id']
        dirname = article_id[-2:]
        filename = f'{article_id}.html'
        filepath = os.path.join(self.dump_dir, dirname, filename)
        pathlib.Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(response.body)
        self.log(f'Saved file {filepath}')

        article = Article(response.meta['article_link'], language=response.meta['article_lang'])

        # set html manually
        article.html = response.body
        article.download_state = 2

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
        filepath = os.path.join(self.dump_dir, dirname, filename)
        with open(filepath, 'w') as f:
            f.write(json.dumps(article_dict))
        self.log(f'Saved file {filepath}')
