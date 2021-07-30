import scrapy

from semeval_8_2021_ia_downloader.semeval_8_2021_ia_downloader.file_io import parse_article_file


class IaArticleSpider(scrapy.Spider):
    name = "IA Article"

    def start_requests(self):
        for article_id, article_link in parse_article_file(self.links_file):
            yield scrapy.Request(article_link,
                                 meta={'article_id': article_id})

    def parse(self, response):
        article_id = response.meta['article_id']
        filename = f'quotes-{article_id}.html'
        with open(filename, 'wb') as f:
            f.write(response.body)
        self.log(f'Saved file {filename}')
