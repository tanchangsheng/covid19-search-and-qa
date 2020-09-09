from elasticsearch import Elasticsearch
from elasticsearch import helpers

url     = "http://localhost"
port    = 9200
index   = "document"
full_doc_index = "full_document"

es_client = Elasticsearch([url],  port=port)

match_all_query = {
  "query": {
    "match_all": {}
  }
}

print("Deleting all documents in document index...")
# es_client.delete_by_query(index, body=match_all_query, request_timeout=30, ignore=404)
# es_client.delete_by_query(full_doc_index, body=match_all_query, request_timeout=30, ignore=404)
es_client.indices.delete(index, ignore_unavailable=True)
es_client.indices.delete(full_doc_index, ignore_unavailable=True)


mapping = {
    "mappings": {
        "dynamic_templates": [
            {
                "strings": {
                    "path_match": "*",
                    "match_mapping_type": "string",
                    "mapping": {
                        "type": "keyword"
                    }
                }
            }
        ],
        "properties": {
            "date": {
                "type": "date"
            },
            "embedding": {
                "type": "dense_vector",
                "dims": 768
            },
            "given_date": {
                "type": "keyword"
            },
            "hash": {
                "type": "keyword"
            },
            "link": {
                "type": "keyword"
            },
            "name": {
                "type": "keyword",
                "fields": {
                    "text": {
                        "type": "text"
                    }
                }
            },
            "sector": {
                "type": "keyword",
                "fields": {
                    "text": {
                        "type": "text"
                    }
                }
            },
            "text": {
                "type": "text"
            },
            "title": {
                "type": "keyword",
                "fields": {
                    "text": {
                        "type": "text"
                    }
                }
            }
        }
    }
}
es_client.indices.create(index=full_doc_index, body=mapping, ignore=400)

import re
import spacy
from spacy.lang.en import English

nlp = English()  # just the language with no model
sentencizer = nlp.create_pipe("sentencizer")
nlp.add_pipe(sentencizer)

MIN_SEG_SIZE = 50
ROUGH_SEG_SIZE = 100

def text2segments(text):
    clean_space = re.sub("\\s+", " ", text)
    doc = nlp(clean_space)
    
    segments = []
    curr_size = 0
    seg_end = 0
    
    for sent in doc.sents:
        curr_size += len(sent)
        sent_end = sent[-1].i
        if curr_size >= ROUGH_SEG_SIZE:
            segments.append(doc[seg_end:sent_end+1].text)
            seg_end = sent_end+1
            curr_size = 0
            
    # if there are leftover tokens from the doc not added to segments        
    if curr_size > 0:
        seg = doc[seg_end:sent_end+1].text
        # if last segment has <=25 tokens
        if curr_size <= MIN_SEG_SIZE:
            if segments:
                segments[-1] += " " + seg
            else:
                segments.append(seg)
        else:
            segments.append(seg)
            
    return segments

import json
import urllib3
import unicodedata
from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse
import tika
from tika import parser
import trafilatura
from lxml import html
import hashlib
from datetime import datetime

def get_root_url(link):
    return urlparse(link).scheme + "://" + urlparse(link).hostname

# return bs object or pdf text content for the page and its root url
def get_page(link):
    page = http.request("GET", link)
    headers = page.headers
    if "Content-Type" in headers:
        if "application/pdf" in headers["Content-Type"]:
            page_content = parser.from_buffer(page.data, TIKA_API)["content"]
            page_type = "pdf"
        if "text/html" in headers["Content-Type"]:
            page_content = bs(page.data.decode('utf-8'), 'lxml')
            page_type = "html"
    root_url = get_root_url(link)
    return page_content, root_url, page_type 

# get main text of from html string
def get_main_text_html(page):
    html_page = html.fromstring(str(page))
    extracted = trafilatura.extract(html_page)
    if extracted:
        return extracted
    print("Using default page text")
    return page.text
    
def extract_pdf_links(page, root_url):
    links = []
    for link in page.select("a[href*='.pdf']"):
        link = link['href']
        if link[:4] != "http":
            link = root_url + link
        links.append(link)
    return links
    
def link2title(link):
    link = link.split("/")[-1]
    file_name = re.match("(.*.pdf)", link.split("/")[-1]).groups()[0]
    file_name = re.sub("(_|-)", " ", file_name)
    file_name = file_name[:-4]
    file_name = file_name.title()
    return file_name

SEGMENT_BATCH_SIZE = 20
# convert segments into document object structure and group them into batches for ingestion later
def prepare_segments(sector, date, title, link, segments):
    prepared_segments = []
    prepared_segments_part = []
    for i,segment in enumerate(segments):
        prepared_segment = {}
        meta = {}
        meta["title"] = title
        meta["sector"] = sector.strip()
        meta["given_date"] = date
        try:
            meta["date"] = str(datetime.strptime(date, "%d %b %Y").date())
        except:
            pass
        meta["link"] = link
        meta["segment_index"] = i
        meta["hash"] = hashlib.sha512((link + segment).encode("UTF-8")).hexdigest()
        prepared_segment["meta"] = meta
        prepared_segment["text"] = segment
        prepared_segments_part.append(prepared_segment)
        if i+1 % SEGMENT_BATCH_SIZE == 0:
            prepared_segments.append(prepared_segments_part)
            prepared_segments_part = []
    if prepared_segments_part:
        prepared_segments.append(prepared_segments_part)
    return prepared_segments


from haystack.database.elasticsearch import ElasticsearchDocumentStore

document_store = ElasticsearchDocumentStore(host="localhost", username="", password="", index="document", custom_mapping=mapping)

def prepare_ingest_full_document(sector, date, title, link, page_content):
    document = {}
    document["title"] = title
    document["sector"] = sector.strip()
    document["given_date"] = date
    try:
        document["date"] = str(datetime.strptime(date, "%d %b %Y").date())
    except:
        pass
    document["link"] = link
    document["hash"] = hashlib.sha512((link + page_content).encode("UTF-8")).hexdigest()
    document["text"] = page_content
    es_client.index(index=full_doc_index, body=document)

def ingest_prepared_segments(prepared_segments):
    for prepared_segment_part in prepared_segments:
        document_store.write_documents(prepared_segment_part)

# split pdf into small segments, then ingest
def process_pdf(sector_name, advisory_date, advisory_title, advisory_link, page_content):

    # index whole document
    prepare_ingest_full_document(sector_name, advisory_date, advisory_title, advisory_link, page_content)

    segments = text2segments(page_content)
    prepared_segments = prepare_segments(sector_name, advisory_date, advisory_title, advisory_link, segments)
    ingest_prepared_segments(prepared_segments)

# split html into small segments, then ingest
# extract all pdf links(append root url if it's relative link), then perform get_page() and ingest_pdf()
def process_html(sector_name, advisory_date, advisory_title, advisory_link, page, site_root_url):

    main_text = get_main_text_html(page)

    # index whole document
    prepare_ingest_full_document(sector_name, advisory_date, advisory_title, advisory_link, main_text)

    segments = text2segments(main_text)
    # prepare segments
    prepared_segments = prepare_segments(sector_name, advisory_date, advisory_title, advisory_link, segments)
    # ingest prepared_segments
    ingest_prepared_segments(prepared_segments)
    
    
    # extract pdf links
    pdf_links = extract_pdf_links(page, site_root_url)
    for link in pdf_links:
        pdf_content, pdf_root_url, _ = get_page(link)
        pdf_title = link2title(link)
        process_pdf(sector_name, advisory_date, pdf_title, link, pdf_content)

def get_advisory_info(advisory_row, root_url):
    advisory_cols = advisory_row.find_all("td")
    advisory_date = advisory_cols[0].text
    advisory_title = unicodedata.normalize("NFKD", advisory_cols[1].text)
    advisory_link = advisory_cols[1].find("a")["href"]
    if advisory_link[:4] != "http":
        advisory_link = root_url + advisory_link
    return advisory_date, advisory_title, advisory_link

def process_sector_block(sector_block, root_url):
    contents = sector_block.find_all("div", {"class": "sfContentBlock"})
    sector_name = contents[0].text.replace("\n", "")
    # skip first row of table as it's the headers
    sector_advisories = contents[1].find_all("tr")[1:]
    
    for advisory_row in sector_advisories:
        advisory_date, advisory_title, advisory_link = get_advisory_info(advisory_row, root_url)
        
        # advisory_link can link to pdf directly or another site
        page_content, site_root_url, page_type = get_page(advisory_link)
        # if pdf, process pdf and ingest doc to ES
        if page_type == "pdf":
            process_pdf(sector_name, advisory_date, advisory_title, advisory_link, page_content)
        # if html check if it there are pdfs on page
        if page_type == "html":
            process_html(sector_name, advisory_date, advisory_title, advisory_link, page_content, site_root_url)

# process the advisories home page bs4
def process_main_page(page, root_url):
    sector_blocks = page.find_all("div", {"class": "sf_cols"})
    for sector_block in sector_blocks:
        process_sector_block(sector_block, root_url)


TIKA_API = "http://localhost:9998/tika"
HOME_LINK = "https://www.moh.gov.sg/covid-19/phase-2-sector-related-advisories"

http = urllib3.PoolManager()
page_content, root_url, _ = get_page(HOME_LINK)
process_main_page(page_content, root_url)




query={
  "aggs": {
    "duplicated_hash": {
      "terms": {
        "field": "hash",
        "min_doc_count": 2,
        "size": 1000
      },
      "aggs": {
        "documents": {
          "top_hits": {
            "size": 10,
            "_source": ["no_source"]
          }
        }
      }
    }
    
  }
}

def remove_duplicates(index):
    has_duplicates = True

    while has_duplicates:

        # query for duplicates
        buckets = es_client.search(index=index, body=query, request_timeout=120)['aggregations']['duplicated_hash']['buckets']

        ids_to_delete = []

        if len(buckets) > 0:
            for bucket in buckets:
                documents = bucket["documents"]["hits"]["hits"]
                # skip first
                for doc in documents[1:]:
                    remove_doc = {
                        '_op_type'  : 'delete',
                        '_index'    : index,
                        '_type'     : '_doc',
                        '_id'       : doc["_id"]
                    }
                    ids_to_delete.append(remove_doc)

            deletes = helpers.parallel_bulk(es_client, ids_to_delete)
            try:
                for item in deletes:
                    pass
            except:
                print("Error encountered during bulk.")
            print(len(ids_to_delete), "duplicates was removed.")
        else:
            has_duplicates = False
            print("No duplicates found.")

remove_duplicates(index)
remove_duplicates(full_doc_index)