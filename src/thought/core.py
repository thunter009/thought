from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd
from notion.collection import Collection, CollectionView
from recordlinkage import Compare, Index

from thought.utils import now


@dataclass
class Metadata:
    """
    The Metadata object. Contains helper functions and generalized metadata
    """

    run_time: datetime = field(default_factory=now, init=False, repr=False)


@dataclass
class CollectionExtension:
    """
    A Collection Extension object which wraps an existing notion-py Collection object
    and adds additional functionality.
    """

    collection: Collection
    metadata: Metadata = field(default_factory=Metadata, init=False, repr=False)

    def dedupe(
        self,
        dataframe: pd.DataFrame | None = None,
        comparison_fields: list[str] | None = None,
        keep_first: bool = True,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Function that dedupes an input dataframe

        Arguments
        ---------
        dataframe: A pandas DataFrame object to perform deduplication on.
                  If a dataframe is not passed,
        comparison_fields: A List of string field names to perform the deduplication
                         with. If not specified, defaults to all columns in the
                         passed dataframe.

        Parameters
        ----------
        keep_first: Keeps the first instance of a duplicate record. If false,
                   will keep the last instance of a record. Defaults to True.

        Returns
        -------
        A pandas dataframe with duplicated records removed
        """
        # if dataframe argument not passed, use internal object records
        if dataframe is None:
            dataframe = self.asdataframe()

        # if comparison fields defaults to all fields if not specified
        if comparison_fields is None:
            comparison_fields = dataframe.columns.to_list()

        # Indexation step
        indexer = Index()
        # TODO: add flexability for different indexing strategies here
        indexer.full()
        candidate_links = indexer.index(dataframe)

        # Comparison step
        compare_cl = Compare()
        # TODO: add flexability for different comparison types here
        for cmp_field in comparison_fields:
            compare_cl.exact(cmp_field, cmp_field, label=cmp_field)
        features = compare_cl.compute(candidate_links, dataframe)

        # Classification step
        num_features = len(comparison_fields)
        matches = features[features.sum(axis=1) == num_features]
        index_to_drop = (
            matches.index.get_level_values(0)
            if keep_first
            else matches.index.get_level_values(1)
        )
        return dataframe.drop(index_to_drop).reset_index()

    def asdataframe(self) -> pd.DataFrame:
        """
        Returns a Collection's Block rows as a pandas data frame using the
        get_all_properties function.
        """
        holder: list[dict[str, Any]] = []
        rows = self.collection.get_rows()
        for block in rows:
            # TODO: add ability to preserve objects here
            row = block.get_all_properties()
            row["id"] = block.id
            holder.append(row)
        return pd.DataFrame(holder)


@dataclass
class CollectionViewExtension:
    """
    A Collection View Extension object which wraps an existing notion-py Collection
    View object and adds additional functionality.
    """

    view: CollectionView
    metadata: Metadata = field(default_factory=Metadata, init=False, repr=False)

    def __post_init__(self) -> None:
        # import ipdb; ipdb.set_trace()
        self.schema = self._get_schema()

    def _get_schema(self) -> dict[str, Any]:
        """
        Get's a Collection View's schema by accessing the parent's collection object
        """
        schema = self.view.parent.collection.get_schema_properties()
        return dict(schema)  # Ensure we return a dict

    def sort(self, field: str, sort_multiselect_values: bool = False) -> None:
        """
        Sorts the collection view by the specified field.

        Args:
            field: The field to sort by
            sort_multiselect_values: Whether to sort multi-select values
        """
        # Implementation of sort method
        pass
