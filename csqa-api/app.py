import sys
import re

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import *
from lib import *
from typing import Optional


app = FastAPI(
    title="Search and Question Answering",
    description="Search and Question Answering on Covid-19 Phase 2 Advisories"
)

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/answers", response_model=List[Answer])
async def get_answers(query: Optional[str] = "", filters:  Optional[str] = None):
    top_k_retriever = 5
    top_k_reader = 3
    if filters and len(filters) > 0:
        filters = filters.split("|")
        answers = finder.get_answers(question=query, filters={"sector": filters}, top_k_retriever=top_k_retriever,
                                     top_k_reader=top_k_reader)
    else:
        answers = finder.get_answers(question=query, top_k_retriever=top_k_retriever, top_k_reader=top_k_reader)
    answers = answers["answers"]
    formatted_answers = []
    for answer in answers:
        if answer["score"] <= 3:
            continue
        answer["context"] = "... " + re.sub("\\s+", " ", answer["context"]) + " ..."
        if answer["answer"] in answer["context"]:
            answer["context"] = answer["context"].replace(answer["answer"], "<b>" + answer["answer"] + "</b>")
        for k in answer["meta"]:
            answer[k] = answer["meta"][k]
        del answer["meta"]
        formatted_answers.append(answer)
    print(formatted_answers)
    return formatted_answers


@app.get("/search", response_model=SearchResponse)
async def search(query: Optional[str] = None, filters: Optional[str] = None, start: Optional[int] = 0,
           size: Optional[int] = 10):
    should_queries = []
    if filters and len(filters) > 0:
        filters = filters.split("|")
        for f in filters:
            should_queries.append({"term": {"sector": f}})

    if not query or len(query) == 0:
        must_query = {
            "match_all": {}
        }
    else:
        must_query = {
            "multi_match": {
                "query": query,
                "fields": [
                    "text",
                    "title.text"
                ]
            }
        }

    full_doc_query = {
        "from": start,
        "size": size,
        "query": {
            "bool": {
                "must": [
                    must_query
                ],
                "filter": [
                    {
                        "bool": {
                            "should": should_queries
                        }
                    }
                ]
            }
        },
        "_source": {
            "excludes": [
                "hash"
            ]
        },
        "highlight": {
            "fields": {
                "text": {}
            }
        }
    }
    hits = es_client.search(index=full_doc_index, body=full_doc_query, request_timeout=30)["hits"]
    total = hits["total"]["value"]
    documents = []
    for hit in hits["hits"]:
        source = hit["_source"]
        text = source["text"]
        text = re.sub("\\s+", " ", text)
        text = text[:200] + " ..."
        source["highlight"] = text
        if "highlight" in hit:
            texts = hit["highlight"]['text']
            formatted_texts = []
            for text in texts:
                text = text.replace("<em>", "<b>")
                text = text.replace("</em>", "</b>")
                text = re.sub("\\s+", " ", text)
                formatted_texts.append(text)
            source["highlight"] = " ... ".join(formatted_texts)
        documents.append(source)
    result = {}
    result["total"] = total
    result["results"] = documents
    print(result)
    return result




if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    uvicorn.run("app:app", host="0.0.0.0", port=port)
