==============================
semeval 2022 task 8 downloader
==============================


.. image:: https://img.shields.io/pypi/v/semeval-8-2022-ia-downloader.svg
        :target: https://pypi.org/project/semeval-8-2022-ia-downloader



Script that scrapes news articles in the 2022 Semeval Task 8 format from the Internet Archive.

Details about the data and the task in the project homepage_.

A pair of articles with id ``0123456789_9876543210`` will be stored in ``output_dir/89/0123456789.{html|json}`` and
``output_dir/10/9876543210.{html|json}`` respectively.

The HTML file contains the web page of the article as obtained from the internet archive.
The json file contains additional information extracted from the page using the package newspaper3k.


The code is available on github_, together with sample_ input data (``sample_data.csv``)

Usage
--------

.. code::

    python3 -m venv venv
    source venv/bin/activate
    pip install semeval_8_2022_ia_downloader
    python -m semeval_8_2022_ia_downloader.cli --links_file=input.csv --dump_dir=output_dir


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _github: https://github.com/euagendas/semeval_8_2022_ia_downloader
.. _homepage: http://www.euagendas.org/semeval2022
.. _sample: https://github.com/euagendas/semeval_8_2022_ia_downloader/blob/master/sample_data.csv
