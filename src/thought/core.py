"""Main module. If include_dataclasses_scaffolding is enabled, you will see Data Class scaffolding here"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List

import pandas as pd
from notion.collection import Collection, CollectionView
from recordlinkage import Compare, Index
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
            # TODO: add ability to preserve objects here
            row = block.get_all_properties()
            row['id'] = block.id
            holder.append(row)
        return pd.DataFrame(holder)


    def sync(self, input_df, id_col='id') -> None:
        import ipdb; ipdb.set_trace()
        pass

@dataclass
class CollectionViewExtension:
    """
    A Collection View Extension object which wraps an existing notion-py Collection View object and adds additional functionality.
    """
    view: CollectionView
    metadata: Metadata = default_field(Metadata(), init=False, repr=False)

    def __post_init__(self):
        # import ipdb; ipdb.set_trace()
        self.schema = self._get_schema()
    
    
    def _get_schema(self):
        '''
            Get's a Collection View's schema by accessing the parent's collection object
        '''
        return self.view.parent.collection.get_schema_properties()

    def _sort_multiselect_record_values(self):
        # iterate over all rows and sort each records property multi-select values
        rows = self.view.collection.get_rows()
        for block in rows:
            field_vals = eval(f'block.{field}')
            if not ascending:
                new_vals = sorted(field_vals, reversed=True)
            else:
                new_vals = sorted(field_vals)
            block.set_property(field, new_vals)

    def _sort_multiselect_schema_values(self):
        pass
    
    def sort(self,
             field: str, 
             sort_multiselect_values: bool = True,
             ascending: bool = True) -> None:
        '''
        Sorts a Collection on a given field in alpha-numeric order.

        Arguments
        ---------

        field: A property to sort the collection view on

        Options
        ---------

        sort_multiselect_values: If the provided field is a multi-select, sorts of the multi-select values before sorting the collection view by the multi-select field
        ascending: Sorts in ascending order by default
        '''
        schema = self.schema

        # map passed field to schema to get property ids
        if sort_multiselect_values:
            self._sort_multiselect_record_values()

        fields = [x for x in schema if field in x['slug']]
        if len(fields) == 1:
            ids = fields[0]['id']
        else:
            logging.info("more than one field matching")

        params = [{
            "direction": "ascending" if ascending else "descending",
            "property": field,
        }]
        ## this doesn't work....why???
        self.view.set("sort",params)
        # result = self.view.build_query(sort=params).execute()
        import ipdb; ipdb.set_trace()
        pass



@dataclass
class Output:
    """
    An Output object which wraps an existing notion-py Block object and adds additional output functionality.
    """
    notion_block: Any
