# -*- coding: utf-8 -*-
'''
Date: Wed Jun 3, 2020
Author: Pei Hua Chen
Purpose: Execution of this script will pull Scopus records for parsed 
    citations copied from the NSF awards pages, clean the search results, and
    write files containing the Scopus records (before and after cleaning) and 
    search result errors.
Notes:
    1. Create a text file named 'Scopus.txt' with your Scopus API key as the
        only line.
    This project requires a key with (1) 'COMPLETE' Scopus API access to get 
        full author lists and funding fields (https://dev.elsevier.com/guides/ScopusSearchViews.htm),
        and (2) an additional access provided by Elsevier Support to get 
        article cited-by lists (https://dev.elsevier.com/support.html).
    2. Scopus keys have an API limit of 20,000 queries per week. It took 
        multiple weeks to pull all these records. Suggested flow in main
        function, but you may need to run these functions in parts when you 
        reach the API limit.
    3. If you have a fast machine, you may need to slow down your calls to the
        Scopus API (uncomment lines 80, 124, 149).

Execution: python pullScopus.py
'''

import pandas as pd, re, string, unidecode
from ScopusScraper import search, fields, quartile, citescore
pd.options.mode.chained_assignment = None

# Read in API key with 'COMPLETE' view authorization
with open('Scopus.txt') as f:
    API_KEY = f.readline()

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
    pd.concat([data, pd.DataFrame.from_records(ssplit, columns=['Title', 'Journal', 'Issue', 'Year'])], 
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
    '''Format query from interdiscplinary set for pulling comparator set.'''
    journal_name, volume, issue = getattr(row, 'publication_name'), str(getattr(row, 'volume')), str(getattr(row, 'issue'))
    if (volume == '' and issue == '') or (type(volume) == float and type(issue) == float):
        query = 'EXACTSRCTITLE(' + journal_name + ')'
    elif volume == '' or type(volume) == float:
        query = 'EXACTSRCTITLE(' + journal_name + ') AND ISSUE(' + issue + ')'
    elif issue == '' or type(issue) == float:
        query = 'EXACTSRCTITLE(' + journal_name + ') AND VOLUME(' + volume + ')'
    else: 
        query = 'EXACTSRCTITLE(' + journal_name + ') AND VOLUME(' + volume + ') AND ISSUE(' + issue + ')'
    return query

def pull_comp(data, output_file):
    '''Pull comparator set and output records.'''
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
    '''Pull cited-by articles for articles in datasets and output records.'''
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


def main():
    '''Main function runs script purpose.'''
    
    '''
    Process manually copied data for Scopus search.
    Files ending in '_manual.csv' originally only contained the first 2-3 
    columns, NSF award identifiers and the copy/pasted citations, and these 
    function calls wrote the additional parsed columns.
    '''
    # citation_split('NSF_CNH_Articles_manual.csv')
    # citation_split('NSF_CNH_Post-2011_Articles_manual.csv')
    
    '''
    Pull Scopus records for CNH-funded articles. Separate by pre-/post-start 
    date 01-01-2012.
    '''
    pubs = pull_manual('..\\Data\\NSF_CNH_Articles_manual.csv', 'Pubs_v1.csv')
    post_CNH = pull_manual('..\\Data\\NSF_CNH_Post-2011_Articles_manual.csv', 'Pubs_CNH_Post-2011.csv')
    
    '''
    Pull comparator set and interdisciplinary cited-by articles after cleaning
    interdisciplinary set. Clean cited-by set.
    '''
    pubs_clean = clean_data(pubs, 'Interdisciplinary')
    pubs_clean['query'] = pubs_clean.apply(lambda row: format_query(row), axis=1)
    pubs_clean.to_csv('Pubs_Final.csv', index=False)
    print('Cleaned interdisciplinary set {} written to Pubs_Final.csv.'.format(len(pubs_clean) / len(pubs)))
    
    comp = pull_comp(pubs_clean, 'Comp_v1.csv')
    
    pubs_cited = pull_cited(pubs_clean, 'PubsCited_v1.csv')
    nrow = len(pubs_cited)
    pubs_cited = clean_data(pubs_cited, 'Interdisciplinary', cited=True, source_df=pubs_clean)
    pubs_cited.to_csv('PubsCited_Final.csv', index=False)
    print('Cleaned interdisciplinary set cited-by {} written to PubsCited_Final.csv.'.format(nrow / len(pubs_cited)))
    
    '''
    Sample interdisciplinary set and pulled cited-by articles after standard 
    cleaning and removing all CNH2 authors NSF grants. Clean cited-by set.
    Note: Since I didn't set a seed before sampling, I read in the list I 
    initially sampled instead of sampling again here.
    '''
    nrow = len(comp)
    comp = clean_data(comp, 'Comparator')
    comp = comp[comp['fund_sponsor'] != 'National Science Foundation']
    comp = comp.query("fund_acr != 'NSF' | fund_sponsor == 'National Sleep Foundation' | fund_sponsor == 'National Stroke Foundation'")
    cnh_auths = [item for sublist in list(pubs_clean['author_ids']) + list(post_CNH['author_ids']) for item in sublist]
    comp_auths_col = comp['author_ids'].to_list()
    remove_indices = []
    for auth in comp_auths_col:
        if [i for i in auth if i in cnh_auths]:
            remove_indices.append(True)
        else: 
            remove_indices.append(False)
    comp['remove'] = remove_indices
    comp = comp[~comp.remove]
    del comp['remove']
    comp.to_csv('Comp_Final.csv', index=False)
    print('Cleaned comparator set {} written to Comp_Final.csv.'.format(nrow / len(comp)))
    
    comp_sample = pd.read_csv('..\\Data\\CompSample.csv')
    # comp_sample = comp_complete.groupby(['Field', 'Quartile']).apply(lambda x: x.sample(frac=0.13)).reset_index(drop=True)
    # Check that sample has correct ratio across field/quartile groups
    # comp_sample['citation_count'] = pd.to_numeric(comp_sample.citation_count)
    # (comp_sample.groupby(['Field', 'Quartile']).count() / len(comp_sample)).scopus_id - (comp_complete.groupby(['Field', 'Quartile']).count() / len(comp_complete)).scopus_id
    comp_sample_cited = pull_cited(comp_sample, 'CompCited_Sample_v1.csv')
    nrow = len(comp_sample_cited)
    comp_sample_cited = clean_data(comp_sample_cited, 'Comparator', cited=True, source_df=comp_sample)
    comp_sample_cited.to_csv('CompCited_Sample_Final.csv', index=False)
    print('Cleaned comparator set cited-by {} written to CompCited_Sample_Final.csv.'.format(nrow / len(comp_sample_cited)))

try:
    main()
except:
    print('Traceback:')
    import traceback
    traceback.print_exc()
    print('Press any key to exit.')
    input()