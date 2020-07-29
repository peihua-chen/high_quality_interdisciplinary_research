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

import pandas as pd, requests, re, string, unidecode
from datetime import datetime
# from collections import Counter, defaultdict
from pathlib import Path


# =============================================================================
#  Read in an API key with 'COMPLETE' view authorization
# =============================================================================
with open('Scopus.txt') as f:
    API_KEY = f.readline()


# =============================================================================
# Generic functions for querying Scopus
# =============================================================================

def _parse_article(entry):
    '''
    Parse Scopus output into pandas dataframe
    '''

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


def _search_scopus(key, query, cursor):
    '''
    Search helper function
    '''

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


def search(key, query):
    '''
    Search Scopus with query string
    '''

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


# =============================================================================
# Quartile, Field, and CiteScore mapping
# From Scopus source list (https://www.scopus.com/sources), we get the Scopus
# within-field journal quartiles. We map the ASJC Code to EC, GI, NS, or
# Other using a predetermined mapping. and choose field by heuristic described
# in the paper. Some "Multidisciplinary" journals covering natural science
# fields, such as "PLoS One", are also mapped to NS. Journals containing
# interdisciplinary . Quartiles remain correct.
# =============================================================================

# d = pd.read_csv(str(Path('../Data/fieldmapping.csv')), index_col='ASJC_Code',
#                 usecols=['ASJC_Code','Mapping']).to_dict()['Mapping']
# scj = pd.read_csv(str(Path('../Data/CiteScore_Metrics_2011-2018_Download_Nov2019.csv')),
#                   encoding='cp1252', dtype=str)
# scj = scj.fillna('')
# scj['Field'] = (scj['Scopus ASJC Code (Sub-subject Area)'].str[:2] + '**').map(d)
# mask = (scj.Title.str.lower().isin(["anais da academia brasileira de ciencias", "archives des sciences", "asm science journal", "beijing daxue xuebao (ziran kexue ban)/acta scientiarum naturalium universitatis pekinensis", "brazilian archives of biology and technology", "bulletin de la societe royale des sciences de liege", "bulletin de la societe vaudoise des sciences naturelles", "bulletin of the georgian national academy of sciences", "chiang mai university journal of natural sciences", "ciencia and engenharia/ science and engineering journal", "comptes rendus de l'academie bulgare des sciences", "current science", "heliyon", "hunan daxue xuebao/journal of hunan university natural sciences", "interciencia", "jilin daxue xuebao (gongxueban)/journal of jilin university (engineering and technology edition)", "journal and proceedings - royal society of new south wales", "journal of advanced research", "journal of king saud university - science", "journal of sciences, islamic republic of iran", "journal of scientific and industrial research", "journal of shanghai jiaotong university (science)", "journal of the indian institute of science", "journal of the national science foundation of sri lanka", "journal of the royal society of new zealand", "journal of zhejiang university, science edition", "kexue tongbao, scientia", "kuwait journal of science", "liaoning gongcheng jishu daxue xuebao (ziran kexue ban)/journal of liaoning technical university (natural science edition)", "maejo international journal of science and technology", "malaysian journal of science", "national science review", "new scientist", "ohio journal of sciences", "pacific science", "papers and proceedings - royal society of tasmania", "philippine journal of science", "plos one", "proceedings of the latvian academy of sciences, section b: natural, exact, and applied sciences", "revista lasallista de investigacion", "royal society open science", "sadhana - academy proceedings in engineering sciences", "sains malaysiana", "science advances", "science bulletin", "science progress", "science, technology and society", "scienceasia", "scientific american", "scientific journal of king faisal university", "scientific reports", "shanghai jiaotong daxue xuebao/journal of shanghai jiaotong university", "shenyang jianzhu daxue xuebao (ziran kexue ban)/journal of shenyang jianzhu university (natural science)", "songklanakarin journal of science and technology", "tianjin daxue xuebao (ziran kexue yu gongcheng jishu ban)/journal of tianjin university science and technology", "tongji daxue xuebao/journal of tongji university", "transactions of tianjin university", "tsinghua science and technology", "universitas scientiarum", "walailak journal of science and technology", "world review of science, technology and sustainable development", "wuhan university journal of natural sciences", "xi'an shiyou daxue xuebao (ziran kexue ban)/journal of xi'an shiyou university, natural sciences edition", "xinan jiaotong daxue xuebao/journal of southwest jiaotong university", "zhongshan daxue xuebao/acta scientiarum natralium universitatis sunyatseni"]))
# scj['Field'][mask] = 'NS'

# rows = defaultdict(lambda:[])
# for row in scj.itertuples():
#     rows[getattr(row, 'Title').lower()].append((getattr(row, 'Quartile'), getattr(row, 'Field'), getattr(row, 'CiteScore')))

# quartile, fields, citescore = {}, {}, {}
# for key, val in rows.items():
#     if len(set([pair[0] for pair in val])) == 1: # i.e. all same quartile
#         f = [pair[1] for pair in val]
#         if 'EC' in f:
#             quartile[key], fields[key], citescore[key] = val[f.index('EC')]
#         else:
#             quartile[key], fields[key], citescore[key] = val[f.index(next(iter(Counter(f))))]
#     else: # i.e. not all same quartile
#         quartile[key], fields[key], citescore[key] = val[0]
# fields['nature'] = 'GI'
# fields['science'] = 'GI'
# fields['proceedings of the national academy of sciences of the united states of america'] = 'GI'

# mapping = {list(quartile)[i]:[quartile[list(quartile)[i]],
#                               fields[list(quartile)[i]],
#                               citescore[list(quartile)[i]]] for i in range(len(quartile))}
# mappingdf = pd.DataFrame.from_dict(mapping, orient='index', columns=['Publication_Name', 'Quartile', 'Field', 'CiteScore'])
# mappingdf.to_csv('journalmapping.csv')

mappingdf = pd.read_csv(str(Path('../Data/journalmapping.csv')))
quartile = dict(zip(mappingdf.Publication_Name, mappingdf.Quartile))
fields = dict(zip(mappingdf.Publication_Name, mappingdf.Field))
citescore = dict(zip(mappingdf.Publication_Name, mappingdf.CiteScore))


# =============================================================================
# Specific functions for pulling this dataset
# =============================================================================

def simple_string(s):
    '''
    Make strings more searchable: lower, remove all non-hyphen punctuation,
    cast accented string to closest ascii string.
    '''

    return unidecode.unidecode(s.lower().translate(str.maketrans('', '', string.punctuation.replace('-', ''))))

def citation_split(file):
    '''
    Split manually copied citations from NSF into components: title, journal, issue, year.
    '''

    data = pd.read_csv('..\\Data\\' + file)
    ssplit = []
    for s in data['Citation'].to_list():
        try: # with issue
            ssplit.append(re.search(r'\'(.+?),\'.*?\s(.+?),.*?\sv.([0-9]+),.*?\s(20[0-9]{2})', s).groups())
        except AttributeError: # no issue
            try:
                temp = list(re.search(r'\'(.+),\'.*?\s(.+?),.*?\s(20[0-9]{2})', s).groups())
                temp.insert(2,'')
                ssplit.append(temp)
            except:
                ssplit.append(['']*4)
    pd.concat([data,
               pd.DataFrame.from_records(ssplit, columns=['Title', 'Journal', 'Issue', 'Year'])],
              axis=1).to_csv(file, index=False)

def pull_manual(input_file, output_file):
    '''
    Pull Scopus records for articles in '_manual.csv' files and output records.
    '''

    data = pd.read_csv('..\\Data\\' + input_file, encoding='utf8', dtype=str)
    docs, error = [], []
    i = 0
    print('Starting... Pull records for', output_file)
    for row in data.itertuples():
        try:
            unique_id = getattr(row, 'unique_id')
        except:
            unique_id = str(getattr(row, 'IR_ID')) + ', ' + str(getattr(row, 'ID'))
        if type(getattr(row, 'Title')) == float:
            error.append((unique_id, getattr(row, 'Citation'), 'docs', 'Citation missing title'))
            continue
        title, journal = simple_string(getattr(row, 'Title')), simple_string(getattr(row, 'Journal'))

        # Search with title and journal
        result_df, remaining_quota = search(API_KEY, 'TITLE(' + title + ') AND SRCTITLE(' + journal + ')')
        # if i % 9: time.sleep(0.5) # API throttle rate = 9 calls/second
        if i % 100 == 0: print('Row ' + i + ', remaining quota:', remaining_quota)
        i += 1
        if type(result_df) == str:
            # Search with title
            result_df, remaining_quota = search(API_KEY, 'TITLE(' + title + ')')
            if type(result_df) == str:
                # Search with full citation
                result_df, remaining_quota = search(API_KEY, 'ALL(' + simple_string(getattr(row, 'Citation')) + ')')
                if type(result_df) == str:
                    error.append([unique_id, 'docs', result_df])
                    continue

        # If found, proceed
        result_df['unique_id'] = unique_id
        docs.append(result_df.head(1))

    docs = pd.concat(docs, axis=0, join='outer', sort=False)
    docs.to_csv(output_file, index=False)
    print('Success.', 'Wrote {} results to'.format(docs.shape[0]), output_file)
    pd.DataFrame(error).to_csv('Error_' + output_file, index=False)
    print('Wrote {} results to'.format(error.shape[0]), 'Error_' + output_file)
    return docs

def format_query(row):
    '''
    Format query from interdiscplinary set for pulling comparator set.
    '''

    journal_name, volume, issue = getattr(row, 'publication_name'), str(getattr(row, 'volume')), str(getattr(row, 'issue'))

    # Some data cleaning for entries that would return error
    if '(Switzerland)' in journal_name:
        journal_name = '"' + journal_name +'"'
    try:
        dt = datetime.strptime(issue, '%d-%b')
        issue = '{0}-{1}'.format(dt.day, dt.month % 100)
    except ValueError:
        try:
            dt = datetime.strptime(issue, '%b-%d')
            issue = '{0}-{1}'.format(dt.month, dt.day % 100)
        except: pass

    if (volume == '' and issue == '') or (volume == 'nan' and issue == 'nan'):
        query = 'EXACTSRCTITLE(' + journal_name + ')'
    elif volume == '' or volume == 'nan':
        query = 'EXACTSRCTITLE(' + journal_name + ') AND ISSUE(' + issue + ')'
    elif issue == '' or issue == 'nan':
        query = 'EXACTSRCTITLE(' + journal_name + ') AND VOLUME(' + volume + ')'
    else:
        query = 'EXACTSRCTITLE(' + journal_name + ') AND VOLUME(' + volume + ') AND ISSUE(' + issue + ')'
    return query

def pull_comp(data, output_file):
    '''
    Pull comparator set and output records.
    '''

    comp_docs, comp_error = [], []
    i = 0
    print('Starting... Pull cited-by records for ' + output_file)
    for query in data['query']:
        result_df, remaining_quota = search(API_KEY, query)
        # if i % 9: time.sleep(0.5) # API throttle rate = 9 calls/second
        if i % 100 == 0: print('Row ' + i + ', remaining quota:', remaining_quota)
        i += 1
        if type(result_df) == str:
            comp_error.append((query, result_df))
        else:
            result_df['query'] = query
            comp_docs.append(result_df)
    comp_docs = pd.concat(comp_docs, axis=0, join='outer', sort=False)
    comp_docs.to_csv(output_file, index=False)
    print('Success.', 'Wrote {} results to'.format(comp_docs.shape[0]), output_file)
    pd.DataFrame(comp_error, columns=['query', 'error_info']).to_csv('Error_' + output_file, index=False)
    print('Wrote {} results to'.format(comp_error.shape[0]), 'Error_' + output_file)
    return comp_docs

def pull_cited(data, output_file):
    '''
    Pull cited-by articles for articles in datasets and output records.
    '''

    cited = []
    eids = data['eid'].to_list()
    if 'unique_id' in data.columns:
        uniq_id = True
        unique_ids = data['unique_id'].to_list()

    print('Starting... Pull cited-by records for ' + output_file)
    for i in range(len(eids)):
        # if i % 9: time.sleep(0.5) # API throttle rate = 9 calls/second
        cited_df, remaining_quota = search(API_KEY, 'REFEID(' + eids[i] + ')')
        if type(cited_df) != str:
            if uniq_id:
                cited_df['award_id'] = re.search(r'(\d+)', unique_ids[i]).group()
                cited_df['unique_id'] = unique_ids[i]
            cited_df['EID'] = eids[i]
            cited.append(cited_df)
        if i % 100 == 0: print('Row ' + i + ', remaining quota:', remaining_quota)
        if remaining_quota == 0:
            print('Stopped at row ' + i + '.')
            break
    cited_docs = pd.concat(cited, axis=0, join='outer', sort=False)
    cited_docs.to_csv(output_file, index=False)
    print('Success.', 'Wrote {} results to'.format(cited_docs.shape[0]), output_file)
    error = pd.DataFrame(set(eids) - set(cited_docs.EID), columns=['error'])
    error.to_csv('Error_' + output_file, index=False)
    print('Wrote {} results to'.format(error.shape[0]), 'Error_' + output_file)
    return cited_docs

def map_fields(df, cited=False, source_df=None):
    '''
    Map Field and Quartile, and Source (original article Field), Cross/Intra,
    and Citation Type for cited-by articles.
    '''

    if not cited:
        df['Field'] = df['publication_name'].str.lower().map(fields)
        df['Quartile'] = df['publication_name'].str.lower().map(quartile)
        df['CiteScore'] = df['publication_name'].str.lower().map(citescore)
    else:
        eid_dict = dict(zip(source_df.eid, source_df.Field))
        df['Source'] = df['EID'].map(eid_dict)
        eid_dict = dict(zip(source_df.eid, source_df.Quartile))
        df["SourceQuartile"] = df["EID"].map(eid_dict)
        df['CrossIntra'] = df.apply(lambda row: 'Intra' if getattr(row, 'Source') == getattr(row, 'Field') else 'Cross', axis=1)
        df['CiteType'] = df.apply(lambda row: getattr(row, 'CrossIntra') + ' ' + getattr(row, 'Source'), axis=1)
    return df

def clean_data(df, dataset, cited=False, source_df=None):
    '''
    Drop duplicates based on eid, map field and quartile, and remove rows with
    non-journal/trade journal aggregation type and unidentified field and
    quartile
    '''

    if not cited:
        df = df.drop_duplicates('eid')
    df = map_fields(df)
    df = df[(df.aggregation_type.isin(['Journal', 'Trade Journal'])) & \
                  (df.Field.isin(['NS', 'EC', 'Other', 'GI'])) & \
                  (df.Quartile.isin(['Quartile 1', 'Quartile 2', 'Quartile 3', 'Quartile 4']))]
    if cited:
        df = map_fields(df, cited, source_df)
    df['Dataset'] = dataset
    return df
