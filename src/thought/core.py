"""Main module. If include_dataclasses_scaffolding is enabled, you will see Data Class scaffolding here"""
from dataclasses import dataclass
from datetime import datetime
from typing import List

import pandas as pd
from recordlinkage import Index, Compare
from notion.collection import Collection
from thought.client import get_client
from thought.utils import default_field, now


@dataclass
class Metadata:
    """
    The Metadata object. Contains helper functions and generalized metadata
    """
    run_time: datetime = default_field(now(), init=False, repr=False)

@dataclass
class CollectionExtension:
    """
    A Collection Extension object which wraps an existing notion-py Collection object and adds additional functionality.
    """
    collection: Collection
    metadata: Metadata = default_field(Metadata(), init=False, repr=False)

    def dedupe(self, 
               dataframe: pd.DataFrame = None, 
               comparison_fields: List = None, 
               keep_first: bool = True,
               **kwargs) -> pd.DataFrame:
        '''
            Function that dedupes an input dataframe

            Arguments
            ---------

            dataframe:          A pandas DataFrame object to perform deduplication on. If a dataframe is not passed, 
            comparison_fields:  A List of string field names to perform the deduplication with. If not specified, defaults to all columns in the passed dataframe.

            Parameters
            ----------
            keep_first:         Keeps the first instance of a duplicate record. If false, will keep the last instance of a record. Defaults to True.

            Returns
            -------
            A pandas dataframe with duplicated records removed
        '''
        # if dataframe argument not passed, use internal object records
        if not dataframe:
            dataframe = self.asdataframe()

        # if comparison fields defaults to all fields if not specified
        if not comparison_fields:
            comparison_fields = dataframe.columns.to_list()
        
        # Indexation step
        indexer = Index()
        # TODO: add flexability for different indexing strategies here
        indexer.full()
        candidate_links = indexer.index(dataframe)

        # Comparison step
        compare_cl = Compare()
        # TODO: add flexability for different comparison types here
        for field in comparison_fields:
            compare_cl.exact(field, field, label=field)
        features = compare_cl.compute(candidate_links, dataframe)

        # Classification step
        num_features = len(comparison_fields)
        matches = features[features.sum(axis=1) == num_features]
        index_to_drop = matches.index.get_level_values(0) if keep_first \
                        else matches.index.get_level_values(1)
        return dataframe.drop(index_to_drop).reset_index()
    
    def asdataframe(self) -> pd.DataFrame:
        '''
            Returns a Collection's Block rows as a pandas data frame using the get_all_properties function.
        '''
        holder = []
        rows = self.collection.get_rows()
        for block in rows:
            row = block.get_all_properties()
            holder.append(row)
        return pd.DataFrame(holder)
