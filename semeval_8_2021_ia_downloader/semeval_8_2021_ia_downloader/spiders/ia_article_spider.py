import os.path

import pandas as pd
import scrapy


def parse_article_file(fpath):
    df = pd.read_csv(fpath, index_col='pair_id')
    for pair_id, row in df.iterrows():
        yield from zip(pair_id.split('_'), row[['link1', 'link2']].values)


class IaArticleSpider(scrapy.Spider):
    name = "IaArticle"

    def start_requests(self):
        for article_id, article_link in parse_article_file(self.links_file):
            yield scrapy.Request(article_link,
                                 meta={'article_id': article_id})

    def parse(self, response):
        article_id = response.meta['article_id']
        filename = f'article-{article_id}.html'
        with open(os.path.join(self.dump_dir, filename), 'wb') as f:
            f.write(response.body)
        self.log(f'Saved file {filename}')
