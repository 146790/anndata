# anndata.h5py is based on h5sparse by Appier Inc. See the copyright and license
# note below.
#
# The design choices of anndata.h5py, however, are fundamentally different. In
# particular, anndata.h5py should be viewed as thin wrapper for h5py that allows
# handling sparse and non-sparse data at the same time. It achieves this by
# extending the functionality of `File` and `Group` objects in the h5py API,
# and providing a new `SparseDataset` object.

# MIT License
#
# Copyright (c) 2017 Appier Inc
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# TODO: think about making all of the below subclasses

import six
import h5py
import numpy as np
import scipy.sparse as ss
from scipy.sparse.sputils import IndexMixin

FORMAT_DICT = {
    'csr': ss.csr_matrix,
    'csc': ss.csc_matrix,
}


def get_format_str(data):
    for format_str, format_class in six.viewitems(FORMAT_DICT):
        if isinstance(data, format_class):
            return format_str
    raise ValueError("Data type {} is not supported.".format(type(data)))


def get_format_class(format_str):
    format_class = FORMAT_DICT.get(format_str, None)
    if format_class is None:
        raise ValueError("Format string {} is not supported."
                         .format(format_str))
    return format_class


class Group(object):
    """The HDF5 group that can detect and create sparse matrix.

    Parameters
    ==========
    h5py_group: h5py.Group
    """

    def __init__(self, h5py_group):
        self.h5py_group = h5py_group

    def __getitem__(self, key):
        h5py_item = self.h5py_group[key]
        if isinstance(h5py_item, h5py.Group):
            if 'h5sparse_format' in h5py_item.attrs:
                # detect the sparse matrix
                return SparseDataset(h5py_item)
            else:
                return Group(h5py_item)
        elif isinstance(h5py_item, h5py.Dataset):
            return h5py_item
        else:
            raise ValueError("Unexpected item type.")

    def __delitem__(self, name):
        self.h5py_group.__delitem__(name)

    def __setitem__(self, key, value):
        self.h5py_group.__setitem__(key, value)

    def keys(self):
        return self.h5py_group.keys()

    def create_dataset(self, name, shape=None, dtype=None, data=None,
                       format='csr', indptr_dtype=np.int64, indices_dtype=np.int32,
                       **kwargs):
        """Create 4 datasets in a group to represent the sparse array."""
        if data is None:
            raise NotImplementedError("Only support create_dataset with "
                                      "existing data.")
        elif isinstance(data, SparseDataset):
            group = self.h5py_group.create_group(name)
            group.attrs['h5sparse_format'] = data.h5py_group.attrs['h5sparse_format']
            group.attrs['h5sparse_shape'] = data.h5py_group.attrs['h5sparse_shape']
            group.create_dataset('data', data=data.h5py_group['data'],
                                 dtype=dtype, **kwargs)
            group.create_dataset('indices', data=data.h5py_group['indices'],
                                 dtype=indices_dtype, **kwargs)
            group.create_dataset('indptr', data=data.h5py_group['indptr'],
                                 dtype=indptr_dtype, **kwargs)
            return SparseDataset(group)
        elif ss.issparse(data):
            group = self.h5py_group.create_group(name)
            group.attrs['h5sparse_format'] = get_format_str(data)
            group.attrs['h5sparse_shape'] = data.shape
            group.create_dataset('data', data=data.data, dtype=dtype, **kwargs)
            group.create_dataset('indices', data=data.indices,
                                 dtype=indices_dtype, **kwargs)
            group.create_dataset('indptr', data=data.indptr,
                                 dtype=indptr_dtype, **kwargs)
            return SparseDataset(group)
        else:
            return self.h5py_group.create_dataset(
                name=name, shape=shape, dtype=dtype, data=data, **kwargs)


class File(Group):
    """The HDF5 file object that can detect and create sparse matrix.

    Parameters
    ==========
    *args, **kwargs: the parameters from h5py.File
    """

    def __init__(self, *args, **kwargs):
        self.h5f = h5py.File(*args, **kwargs)
        self.h5py_group = self.h5f

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.h5f.__exit__(exc_type, exc_value, traceback)

    def close(self):
        self.h5f.close()


class SparseDataset(IndexMixin):
    """The HDF5 sparse matrix dataset.

    Parameters
    ==========
    h5py_group: h5py.Dataset
    """

    def __init__(self, h5py_group):
        self.h5py_group = h5py_group

    def __repr__(self):
        return ('<HDF5 sparse dataset: format \'{}\', shape {}, type \'{}\'>'
                .format(
                    self.format_str,
                    self.shape, self.h5py_group['data'].dtype.str))
    
    @property
    def format_str(self):
        return self.h5py_group.attrs['h5sparse_format']

    def __getitem__(self, key):
        row, col = self._unpack_index(key)
        if self.format_str == 'csr':
            if (isinstance(col, (int, np.int))
                or any((col.start, col.stop, col.step))):
                raise ValueError(
                    'Slicing csr matrices is only possible along rows.')
            key = row
        else:
            if (isinstance(row, (int, np.int))
                or any((row.start, row.stop, row.step))):
                raise ValueError(
                    'Slicing csc matrices is only possible along columns.')
            key = col
        if isinstance(key, (int, np.int)):
            start = key
            stop = start + 1
            key = slice(start, stop)
        if isinstance(key, slice):
            if key.step not in {None, 1}:
                raise NotImplementedError("Index step is not supported.")
            start = key.start
            stop = key.stop
            if stop is not None and stop > 0:
                stop += 1
            if start is not None and start < 0:
                start -= 1
            indptr_slice = slice(start, stop)
            indptr = self.h5py_group['indptr'][indptr_slice]
            data = self.h5py_group['data'][indptr[0]:indptr[-1]]
            indices = self.h5py_group['indices'][indptr[0]:indptr[-1]]
            indptr -= indptr[0]
            if self.format_str == 'csr':
                shape = (indptr.size - 1, self.shape[1])
            else:
                shape = (self.shape[0], indptr.size - 1)
        else:
            raise NotImplementedError("Only support one slice as index.")

        format_class = get_format_class(self.format_str)
        return format_class((data, indices, indptr), shape=shape)

    @property
    def shape(self):
        return tuple(self.h5py_group.attrs['h5sparse_shape'])

    @property
    def value(self):
        data = self.h5py_group['data'].value
        indices = self.h5py_group['indices'].value
        indptr = self.h5py_group['indptr'].value
        shape = self.h5py_group.attrs['h5sparse_shape']
        format_class = get_format_class(self.format_str)
        return format_class((data, indices, indptr), shape=shape)

    def append(self, sparse_matrix):
        shape = self.h5py_group.attrs['h5sparse_shape']

        if self.format_str != get_format_str(sparse_matrix):
            raise ValueError("Format not the same.")

        if self.format_str == 'csr':
            # data
            data = self.h5py_group['data']
            orig_data_size = data.shape[0]
            new_shape = (orig_data_size + sparse_matrix.data.shape[0],)
            data.resize(new_shape)
            data[orig_data_size:] = sparse_matrix.data

            # indptr
            indptr = self.h5py_group['indptr']
            orig_data_size = indptr.shape[0]
            append_offset = indptr[-1]
            new_shape = (orig_data_size + sparse_matrix.indptr.shape[0] - 1,)
            indptr.resize(new_shape)
            indptr[orig_data_size:] = (sparse_matrix.indptr[1:].astype(np.int64)
                                       + append_offset)

            # indices
            indices = self.h5py_group['indices']
            orig_data_size = indices.shape[0]
            new_shape = (orig_data_size + sparse_matrix.indices.shape[0],)
            indices.resize(new_shape)
            indices[orig_data_size:] = sparse_matrix.indices

            # shape
            self.h5py_group.attrs['h5sparse_shape'] = (
                shape[0] + sparse_matrix.shape[0],
                max(shape[1], sparse_matrix.shape[1]))
        else:
            raise NotImplementedError("The append method for format {} is not "
                                      "implemented.".format(self.format_str))
