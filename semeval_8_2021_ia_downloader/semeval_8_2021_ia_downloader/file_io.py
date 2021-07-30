import pandas as pd


def parse_article_file(fpath):
    df = pd.read_csv(fpath, index_col='pair_id')
    for pair_id, row in df.iterrows():
        yield from zip(pair_id.split('_'), row[['link1', 'link2']].values)


if __name__ == '__main__':
    for article_id, article_link in parse_article_file('../../test_data.csv'):
        print(article_id, article_link)
