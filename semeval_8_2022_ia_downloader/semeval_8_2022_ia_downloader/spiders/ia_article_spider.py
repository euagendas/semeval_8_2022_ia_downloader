import scrapy
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError

from semeval_8_2022_ia_downloader.cli import parse_article, get_remaining_articles


class IaArticleSpider(scrapy.Spider):
    name = "IaArticle"

    def start_requests(self):
        for article_id, article_link, article_lang in get_remaining_articles(self.links_file, self.dump_dir,
                                                                             self.min_text_length):
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

        if failure.check(HttpError):
            # you can get the response
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        elif failure.check(DNSLookupError):
            # this is the original request
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        elif failure.check(TimeoutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)

    def parse(self, response):
        parse_article(self.dump_dir,
                      response.meta['article_id'],
                      response.meta['article_link'],
                      response.meta['article_lang'],
                      html=response.body)
