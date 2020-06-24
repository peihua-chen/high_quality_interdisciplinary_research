# -*- coding: utf-8 -*-
'''
Date: Wed Jun 3, 2020
Author: Pei Hua Chen
Purpose: This script provides functions for parsing citations and querying 
    the Scopus Search API with 'Complete' view. See 
    https://dev.elsevier.com/tips/ScopusSearchTips.htm for more information.
    This script also constructs our dictionaries for journal field and 
    quartile mappings.
'''

import pandas as pd, requests, csv
from collections import Counter, defaultdict

# Parse Scopus output into pandas dataframe
def _parse_article(entry):
    try:
        scopus_id = entry['dc:identifier'][10:]
    except:
        scopus_id = None
    try:
        eid = entry['eid']
    except:
        eid = None
    try:
        title = entry['dc:title']
    except:
        title = None
    try:
        publicationname = entry['prism:publicationName']
    except:
        publicationname = None
    try:
        issn = entry['prism:issn']
    except:
        issn = None
    try:
        isbn = entry['prism:isbn']
    except:
        isbn = None
    try:
        eissn = entry['prism:eIssn']
    except:
        eissn = None
    try:
        volume = entry['prism:volume']
    except:
        volume = None
    try:
        issue = entry['prism:issueIdentifier']
    except:
        issue = None
    try:
        pagerange = entry['prism:pageRange']
    except:
        pagerange = None
    try:
        coverdate = entry['prism:coverDate']
    except:
        coverdate = None
    try:
        doi = entry['prism:doi']
    except:
        doi = None
    try:
        description = entry['dc:description']
    except:
        description = None
    try:
        citationcount = int(entry['citedby-count'])
    except:
        citationcount = None
    try:
        affiliation = entry['affiliation']
    except:
        affiliation = None
    try:
        aggregationtype = entry['prism:aggregationType']
    except:
        aggregationtype = None
    try:
        sub_dc = entry['subtypeDescription']
    except:
        sub_dc = None
    try:
        author_entry = entry['author']
        author_id_list = [auth_entry['authid'] for auth_entry in author_entry]
        author_name_list = [auth_entry['authname'] for auth_entry in author_entry]
    except:
        author_id_list = list()
        author_name_list = list()
    try:
        auth_keywords = entry['authkeywords']
    except:
        auth_keywords = None
    try:
        fund_acr = entry['fund-acr']
    except:
        fund_acr = None
    try:
        fund_no = entry['fund-no']
    except:
        fund_no = None
    try:
        fund_sponsor = entry['fund-sponsor']
    except:
        fund_sponsor = None
    try:
        link_list = entry['link']
        full_text_link = None
        for link in link_list:
            if link['@ref'] == 'full-text':
                full_text_link = link['@href']
    except:
        full_text_link = None

    return pd.Series({'scopus_id': scopus_id, 'eid': eid, 'title': title, 'publication_name':publicationname,\
            'issn': issn, 'isbn': isbn, 'eissn': eissn, 'volume': volume, 'issue': issue, 'page_range': pagerange,\
            'cover_date': coverdate, 'doi': doi, 'description': description,'citation_count': citationcount, \
            'affiliation': affiliation, 'aggregation_type': aggregationtype, 'subtype_description': sub_dc, \
            'author_name_list': author_name_list, 'author_ids': author_id_list, 'auth_keywords': auth_keywords, \
            'fund_acr': fund_acr, 'fund_no': fund_no, 'fund_sponsor': fund_sponsor, 'full_text': full_text_link})

# Search helper function
def _search_scopus(key, query, cursor):
    url = 'https://api.elsevier.com/content/search/scopus'
    params = {'apikey': key, 'query': query, 'cursor': cursor, 
           'httpAccept': 'application/json', 'view':'COMPLETE'}
    r = requests.get(url, params=params)
    remaining_quota = int(r.headers['X-RateLimit-Remaining'])
    js = r.json()
    try:
        total_results = int(js['search-results']['opensearch:totalResults'])
        cursor = js['search-results']['cursor']['@next']
        entries = js['search-results']['entry']
        if len(entries[0]) == 2:
            return entries[0]['error'], remaining_quota
        result_df = pd.DataFrame([_parse_article(entry) for entry in entries])
        return result_df, total_results, cursor, remaining_quota
    except:
        return r.text, remaining_quota

# Run search and paginate - use this
def search(key, query):
    x = _search_scopus(key, query, '*')
    if len(x) == 4:
        result_df, total_results, cursor, remaining_quota = x
        index = result_df.shape[0]
        
        while index < total_results:
            df, total_results, cursor, remaining_quota = _search_scopus(key, query, cursor)
            result_df = result_df.append(df, ignore_index=True)
            index = result_df.shape[0]
        return result_df, remaining_quota
    else:
        return x[0], x[1]
    
'''
Quartile, Field, and CiteScore mapping
From Scopus source list (https://www.scopus.com/sources), we get the Scopus 
within-field journal quartiles. We map the ASJC Code to EC, GI, NS, or 
Other using a predetermined mapping. and choose field by heuristic described 
in the paper.
'''
d = pd.read_csv('..\\Data\\fieldmapping.csv')[['ASJC_Code','Mapping']].set_index('ASJC_Code').to_dict()['Mapping']
scj = pd.read_csv("..\\Data\\CiteScore_Metrics_2011-2018_Download_Nov2019.csv", encoding='cp1252', dtype=str)
scj = scj.fillna('')
scj['Field'] = (scj['Scopus ASJC Code (Sub-subject Area)'].str[:2] + '**').map(d)
rows = defaultdict(lambda:[])
for row in scj.itertuples():
    rows[getattr(row, 'Title').lower()].append((getattr(row, 'Quartile'), getattr(row, 'Field'), getattr(row, 'CiteScore')))

quartile, fields, citescore = {}, {}, {}
for key, val in rows.items():
    if len(set([pair[0] for pair in val])) == 1: # i.e. all same quartile
        f = [pair[1] for pair in val]
        if 'EC' in f:
            quartile[key], fields[key], citescore[key] = val[f.index('EC')]
        else:
            quartile[key], fields[key], citescore[key] = val[f.index(next(iter(Counter(f))))]
    else: # i.e. not all same quartile
        quartile[key], fields[key], citescore[key] = val[0]
fields['nature'] = 'GI'
fields['science'] = 'GI'
fields['proceedings of the national academy of sciences of the united states of america'] = 'GI'

# mapping = {list(quartile)[i]:[quartile[list(quartile)[i]],
#                               fields[list(quartile)[i]],
#                               citescore[list(quartile)[i]]] for i in range(len(quartile))}
# mappingdf = pd.DataFrame.from_dict(mapping, orient='index', columns=['Quartile', 'Field', 'CiteScore'])
# mappingdf.to_csv('journalmapping.csv')
