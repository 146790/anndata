See all releases `here <https://github.com/theislab/anndata/releases>`_. The following lists selected improvements.


**March 19, 2018**: version 0.5.6

1. better memory efficiency in loom exports
2. 'outer join' concatenation   
3. bug fixes and consistency updates

.. warning::

    There was a bug in :func:`~anndata.AnnData.concatenate` in versions 0.5.2,
    0.5.3 and 0.5.4: variable names were not assigned correctly. Was fixed in
    version 0.5.5.

**February 9, 2018**: version 0.5

1. inform about duplicates in :class:`~anndata.AnnData.var_names` and resolve them using :func:`~anndata.AnnData.var_names_make_unique`
2. by default, generate unique observation names in :func:`~anndata.AnnData.concatenate`
3. automatically remove unused categories after slicing
4. read/write `.loom` files using loompy 2
5. some IDE-backed improvements


**December 29, 2017**: version 0.4.2

1. fixed read/write for a few text file formats
2. read `UMI tools <https://github.com/CGATOxford/UMI-tools>`_ files: :func:`~anndata.read_umi_tools`


**December 23, 2017**: version 0.4

1. towards a common file format for exchanging :class:`~anndata.AnnData` with
   packages such as Seurat and SCDE by reading and writing `.loom
   <http://loompy.org>`_ files
2. :class:`~anndata.AnnData`
   provides scalability beyond dataset sizes that fit into memory: see this
   `blog post
   <http://falexwolf.de/blog/171223_AnnData_indexing_views_HDF5-backing/>`_
3. :class:`~anndata.AnnData` has a :class:`~anndata.AnnData.raw` attribute
   that simplifies storing the data matrix when you consider it "raw": see the
   `clustering tutorial
   <https://github.com/theislab/scanpy_usage/tree/master/170505_seurat>`_
