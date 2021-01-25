from haystack import Finder
from haystack.reader.farm import FARMReader
from haystack.retriever.sparse import ElasticsearchRetriever
from haystack.document_store.elasticsearch import ElasticsearchDocumentStore

document_store = ElasticsearchDocumentStore(host="localhost", username="", password="", index="document")
retriever = ElasticsearchRetriever(document_store=document_store)
reader = FARMReader(model_name_or_path="deepset/roberta-base-squad2", use_gpu=True)
finder = Finder(reader, retriever)


from elasticsearch import Elasticsearch

url     = "http://localhost"
port    = 9200
index   = "document"
full_doc_index = "full_document"

es_client = Elasticsearch([url],  port=port)