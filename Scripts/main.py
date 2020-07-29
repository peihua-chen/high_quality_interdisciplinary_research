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

Execution: Run script line-by-line as needed.
'''

import pandas as pd
from functions import pull_manual, pull_comp, pull_cited, format_query, clean_data
pd.options.mode.chained_assignment = None


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
comp = comp[~comp.eid.isin(pubs_clean.eid)]
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
