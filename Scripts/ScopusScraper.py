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

import pandas as pd, requests
from collections import Counter

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
Quartile and CiteScore mapping
From a Scopus source list, we get the Scopus within-field journal quartiles.
'''
citescore = pd.read_csv('..\\Data\\..\\Data\\ScopusJournals__CiteScore_Metrics_2011-2018_download.csv',
                    header=1, encoding='utf8', dtype=str)
quartile = dict(zip(citescore.Title.str.lower(), citescore.Quartile))
citescore = dict(zip(citescore.Title.str.lower(), citescore.CiteScore))

'''
Field mapping
From the Scopus source list, I created column 'x2' by joining columns from
'1000\General' to '3600\Health Professions' with '&.' I removed 'General' or
replaced it with 'Natural Science' if the only entry was 'General' and NS was 
an appropriate classification. The Scopus fields were mapped to EC, GI, NS, 
or Other below.
'''
d = pd.read_csv('..\\Data\\fieldmapping.csv')[['Field','Mapping']].set_index('Field').to_dict()['Mapping']
def get_disc(fields, d):
    fields = [d.get(i, i) for i in fields]
    if fields.count('NS') == len(fields): 
        return 'NS'
    elif fields.count('EC') == len(fields):
        return 'EC'
    elif 'EC' in fields:
        return 'EC'
    else:
        return next(iter(Counter(fields)))
    
scopus_journals = pd.read_csv('journals_october_2019.csv', encoding='utf8', dtype=str)
scopus_journals = scopus_journals[scopus_journals['Source Type'].isin(['Journal', 'Trade Journal'])]
scopus_journals = scopus_journals[['Source Title (Medline-sourced journals are indicated in Green)', 'x2']]
scopus_journals['fields_list'] = scopus_journals.x2.apply(lambda x: list(filter(None, x.split('&'))))
scopus_journals['Field'] = scopus_journals.fields_list.apply(lambda x: get_disc(x, d))
fields = dict(zip(scopus_journals['Source Title (Medline-sourced journals are indicated in Green)'].str.lower(), scopus_journals.Field))
fields['nature'] = 'GI'
fields['science'] = 'GI'
fields['proceedings of the national academy of sciences of the united states of america'] = 'GI'