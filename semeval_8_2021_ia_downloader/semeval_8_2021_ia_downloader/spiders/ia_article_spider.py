import json
import os.path

import pandas as pd
import scrapy
from newspaper import Article


def parse_article_file(fpath):
    df = pd.read_csv(fpath, index_col='pair_id')
    for pair_id, row in df.iterrows():
        yield from zip(pair_id.split('_'),
                       row[['link1', 'link2']].values,
                       row[['lang1', 'lang2']].values, )


class IaArticleSpider(scrapy.Spider):
    name = "IaArticle"

    def start_requests(self):
        for article_id, article_link, article_lang in parse_article_file(self.links_file):
            yield scrapy.Request(article_link,
                                 meta={'article_id': article_id,
                                       'article_link': article_link,
                                       'article_lang': article_lang,
                                       })

    def parse(self, response):
        article_id = response.meta['article_id']
        filename = f'article-{article_id}.html'
        with open(os.path.join(self.dump_dir, filename), 'wb') as f:
            f.write(response.body)
        self.log(f'Saved file {filename}')

        article = Article(response.meta['article_link'], language=response.meta['article_lang'])

        # set html manually
        article.html = response.body
        # need to set download_state to 2 for this to work
        article.download_state = 2
        article.parse()

        filename = f'article-{article_id}.json'
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
                            publish_date=article.publish_date.ctime(),
                            summary=article.summary,
                            article_html=article.article_html,
                            meta_description=article.meta_description,
                            meta_lang=article.meta_lang,
                            meta_favicon=article.meta_favicon,
                            meta_data=dict(article.meta_data),
                            canonical_link=article.canonical_link
                            )
        with open(os.path.join(self.dump_dir, filename), 'w') as f:
            f.write(json.dumps(article_dict))
        self.log(f'Saved file {filename}')
