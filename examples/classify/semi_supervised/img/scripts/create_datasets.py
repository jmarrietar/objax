#!/usr/bin/env python

# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Script to download all datasets and create .tfrecord files.
"""

import collections
import gzip
import os, fnmatch
import tarfile
import tempfile
from urllib import request
import matplotlib.image as mpimg 
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
import scipy.io
import tensorflow as tf
from absl import app
from tqdm import trange

from libml.data import core
from objax.util import EasyDict
from objax.util.image import to_png

URLS = {
    'svhn': 'http://ufldl.stanford.edu/housenumbers/{}_32x32.mat',
    'cifar10': 'https://www.cs.toronto.edu/~kriz/cifar-10-matlab.tar.gz',
    'cifar100': 'https://www.cs.toronto.edu/~kriz/cifar-100-matlab.tar.gz',
    'stl10': 'http://ai.stanford.edu/~acoates/stl10/stl10_binary.tar.gz',
    'mnist': 'http://yann.lecun.com/exdb/mnist/{}',
}


def _encode_png(images):
    return [to_png(images[x]) for x in trange(images.shape[0], desc='PNG Encoding', leave=False)]


def _load_svhn():
    splits = collections.OrderedDict()
    for split in ['train', 'test', 'extra']:
        with tempfile.NamedTemporaryFile() as f:
            request.urlretrieve(URLS['svhn'].format(split), f.name)
            data_dict = scipy.io.loadmat(f.name)
        dataset = {}
        dataset['images'] = np.transpose(data_dict['X'], [3, 0, 1, 2])
        dataset['images'] = _encode_png(dataset['images'])
        dataset['labels'] = data_dict['y'].reshape((-1))
        # SVHN raw data uses labels from 1 to 10; use 0 to 9 instead.
        dataset['labels'] %= 10  # Label number 10 is for 0.
        splits[split] = dataset
    return splits


def _load_stl10():
    def unflatten(images):
        return np.transpose(images.reshape((-1, 3, 96, 96)), [0, 3, 2, 1])

    with tempfile.NamedTemporaryFile() as f:
        if tf.io.gfile.exists('stl10/stl10_binary.tar.gz'):
            f = tf.io.gfile.GFile('stl10/stl10_binary.tar.gz', 'rb')
        else:
            request.urlretrieve(URLS['stl10'], f.name)
        tar = tarfile.open(fileobj=f)
        train_x = tar.extractfile('stl10_binary/train_X.bin')
        train_y = tar.extractfile('stl10_binary/train_y.bin')
        test_x = tar.extractfile('stl10_binary/test_X.bin')
        test_y = tar.extractfile('stl10_binary/test_y.bin')
        unlabeled_x = tar.extractfile('stl10_binary/unlabeled_X.bin')
        train_set = {'images': np.frombuffer(train_x.read(), dtype=np.uint8),
                     'labels': np.frombuffer(train_y.read(), dtype=np.uint8) - 1}
        test_set = {'images': np.frombuffer(test_x.read(), dtype=np.uint8),
                    'labels': np.frombuffer(test_y.read(), dtype=np.uint8) - 1}
        _imgs = np.frombuffer(unlabeled_x.read(), dtype=np.uint8)
        unlabeled_set = {'images': _imgs,
                         'labels': np.zeros(100000, dtype=np.uint8)}
        fold_indices = tar.extractfile('stl10_binary/fold_indices.txt').read()

    train_set['images'] = _encode_png(unflatten(train_set['images']))
    test_set['images'] = _encode_png(unflatten(test_set['images']))
    unlabeled_set['images'] = _encode_png(unflatten(unlabeled_set['images']))
    return dict(train=train_set, test=test_set, unlabeled=unlabeled_set,
                files=[EasyDict(filename="stl10_fold_indices.txt", data=fold_indices)])


def _load_cifar10():
    def unflatten(images):
        return np.transpose(images.reshape((images.shape[0], 3, 32, 32)),
                            [0, 2, 3, 1])

    with tempfile.NamedTemporaryFile() as f:
        request.urlretrieve(URLS['cifar10'], f.name)
        tar = tarfile.open(fileobj=f)
        train_data_batches, train_data_labels = [], []
        for batch in range(1, 6):
            data_dict = scipy.io.loadmat(tar.extractfile('cifar-10-batches-mat/data_batch_{}.mat'.format(batch)))
            train_data_batches.append(data_dict['data'])
            train_data_labels.append(data_dict['labels'].flatten())
        train_set = {'images': np.concatenate(train_data_batches, axis=0),
                     'labels': np.concatenate(train_data_labels, axis=0)}
        data_dict = scipy.io.loadmat(tar.extractfile('cifar-10-batches-mat/test_batch.mat'))
        test_set = {'images': data_dict['data'],
                    'labels': data_dict['labels'].flatten()}
    train_set['images'] = _encode_png(unflatten(train_set['images']))
    test_set['images'] = _encode_png(unflatten(test_set['images']))
    return dict(train=train_set, test=test_set)

def _load_voets():

    IMG_SIZE = 100

    DIR = "/Users/jmarrietar/Dropbox/11_Semestre/Maestria/code/data/"
    #DIR = "/Volumes/APOLLOM110/server/jama16-retina-replication-master/data/eyepacs"
    TRAIN_DIR = os.path.join(DIR, "train")
    TEST_DIR = os.path.join(DIR, "test")

    # Train dataset
    train_0_imgs = [
        os.path.join(TRAIN_DIR, "0", x)
        for x in fnmatch.filter(os.listdir(os.path.join(TRAIN_DIR, "0")), "*.jpg")
    ]
    train_1_imgs = [
        os.path.join(TRAIN_DIR, "1", x)
        for x in fnmatch.filter(os.listdir(os.path.join(TRAIN_DIR, "1")), "*.jpg")
    ]
    train_imgs = train_0_imgs + train_1_imgs

    train_set = {}
    
    
    train_set["images"] = np.array([np.array(Image.open(fname).resize((IMG_SIZE, IMG_SIZE))) for fname in train_imgs])
     
    train_set["labels"] = np.array(
        list(np.zeros(len(train_0_imgs), dtype=np.int8))
        + list(np.ones(len(train_1_imgs), dtype=np.int8))
    )

    # Test dataset
    test_0_imgs = [
        os.path.join(TEST_DIR, "0", x)
        for x in fnmatch.filter(os.listdir(os.path.join(TEST_DIR, "0")), "*.jpg")
    ]
    test_1_imgs = [
        os.path.join(TEST_DIR, "1", x)
        for x in fnmatch.filter(os.listdir(os.path.join(TEST_DIR, "1")), "*.jpg")
    ]
    test_imgs = test_0_imgs + test_1_imgs

    test_set = {}
    test_set["images"] = np.array([np.array(Image.open(fname).resize((IMG_SIZE, IMG_SIZE))) for fname in test_imgs])

    test_set["labels"] = np.array(
        list(np.zeros(len(test_0_imgs), dtype=np.int8))
        + list(np.ones(len(test_1_imgs), dtype=np.int8))
    )

    train_set["images"] = _encode_png(train_set["images"])
    test_set["images"] = _encode_png(test_set["images"])
    return dict(train=train_set, test=test_set)

def _load_cifar100():
    def unflatten(images):
        return np.transpose(images.reshape((images.shape[0], 3, 32, 32)), [0, 2, 3, 1])

    with tempfile.NamedTemporaryFile() as f:
        request.urlretrieve(URLS['cifar100'], f.name)
        tar = tarfile.open(fileobj=f)
        data_dict = scipy.io.loadmat(tar.extractfile('cifar-100-matlab/train.mat'))
        train_set = {'images': data_dict['data'],
                     'labels': data_dict['fine_labels'].flatten()}
        data_dict = scipy.io.loadmat(tar.extractfile('cifar-100-matlab/test.mat'))
        test_set = {'images': data_dict['data'],
                    'labels': data_dict['fine_labels'].flatten()}
    train_set['images'] = _encode_png(unflatten(train_set['images']))
    test_set['images'] = _encode_png(unflatten(test_set['images']))
    return dict(train=train_set, test=test_set)


def _load_mnist():
    image_filename = '{}-images-idx3-ubyte.gz'
    label_filename = '{}-labels-idx1-ubyte.gz'
    split_files = [('train', 'train'), ('test', 't10k')]
    splits = {}
    for split, split_file in split_files:
        with tempfile.NamedTemporaryFile() as f:
            url = URLS['mnist'].format(image_filename.format(split_file))
            print(url)
            request.urlretrieve(url, f.name)
            with gzip.GzipFile(fileobj=f, mode='r') as data:
                assert _read32(data) == 2051
                n_images = _read32(data)
                row = _read32(data)
                col = _read32(data)
                images = np.frombuffer(data.read(n_images * row * col), dtype=np.uint8)
                images = images.reshape((n_images, row, col, 1))
        with tempfile.NamedTemporaryFile() as f:
            request.urlretrieve(URLS['mnist'].format(label_filename.format(split_file)), f.name)
            with gzip.GzipFile(fileobj=f, mode='r') as data:
                assert _read32(data) == 2049
                n_labels = _read32(data)
                labels = np.frombuffer(data.read(n_labels), dtype=np.uint8)
        splits[split] = {'images': _encode_png(images), 'labels': labels}
    return splits


def _load_fashionmnist():
    image_filename = '{}-images-idx3-ubyte'
    label_filename = '{}-labels-idx1-ubyte'
    split_files = [('train', 'train'), ('test', 't10k')]
    splits = {}
    for split, split_file in split_files:
        with tempfile.NamedTemporaryFile() as f:
            request.urlretrieve(URLS['fashion_mnist'].format(image_filename.format(split_file)), f.name)
            with gzip.GzipFile(fileobj=f, mode='r') as data:
                assert _read32(data) == 2051
                n_images = _read32(data)
                row = _read32(data)
                col = _read32(data)
                images = np.frombuffer(data.read(n_images * row * col), dtype=np.uint8)
                images = images.reshape((n_images, row, col, 1))
        with tempfile.NamedTemporaryFile() as f:
            request.urlretrieve(URLS['fashion_mnist'].format(label_filename.format(split_file)), f.name)
            with gzip.GzipFile(fileobj=f, mode='r') as data:
                assert _read32(data) == 2049
                n_labels = _read32(data)
                labels = np.frombuffer(data.read(n_labels), dtype=np.uint8)
        splits[split] = {'images': _encode_png(images), 'labels': labels}
    return splits


def _read32(data):
    dt = np.dtype(np.uint32).newbyteorder('>')
    return np.frombuffer(data.read(4), dtype=dt)[0]


def _int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def _bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def _save_as_tfrecord(data, filename):
    assert len(data['images']) == len(data['labels'])
    filename = os.path.join(core.DATA_DIR, filename + '.tfrecord')
    print('Saving dataset:', filename)
    with tf.io.TFRecordWriter(filename) as writer:
        for x in trange(len(data['images']), desc='Building records'):
            feat = dict(image=_bytes_feature(data['images'][x]),
                        label=_int64_feature(data['labels'][x]))
            record = tf.train.Example(features=tf.train.Features(feature=feat))
            writer.write(record.SerializeToString())
    print('Saved:', filename)


def _is_installed(name, checksums):
    for subset, checksum in checksums.items():
        filename = os.path.join(core.DATA_DIR, '%s-%s.tfrecord' % (name, subset))
        if not tf.io.gfile.exists(filename):
            return False
    return True


def _save_files(files, *args, **kwargs):
    del args, kwargs
    for folder in frozenset(os.path.dirname(x) for x in files):
        tf.io.gfile.makedirs(os.path.join(core.DATA_DIR, folder))
    for filename, contents in files.items():
        with tf.io.gfile.GFile(os.path.join(core.DATA_DIR, filename), 'w') as f:
            f.write(contents)


def _is_installed_folder(name, folder):
    return tf.io.gfile.exists(os.path.join(core.DATA_DIR, name, folder))


CONFIGS = {
    #'cifar10': dict(loader=_load_cifar10, checksums=dict(train=None, test=None)),
    'voets': dict(loader=_load_voets, checksums=dict(train=None, test=None)),
    #'cifar100': dict(loader=_load_cifar100, checksums=dict(train=None, test=None)),
    #'svhn': dict(loader=_load_svhn, checksums=dict(train=None, test=None, extra=None)),
    #'stl10': dict(loader=_load_stl10, checksums=dict(train=None, test=None)),
    #'mnist': dict(loader=_load_mnist, checksums=dict(train=None, test=None)),
}


def main(argv):
    if len(argv[1:]):
        subset = set(argv[1:])
    else:
        subset = set(CONFIGS.keys())
    tf.io.gfile.makedirs(core.DATA_DIR)
    for name, config in CONFIGS.items():
        if name not in subset:
            continue
        if 'is_installed' in config:
            if config['is_installed']():
                print('Skipping already installed:', name)
                continue
        elif _is_installed(name, config['checksums']):
            print('Skipping already installed:', name)
            continue
        print('Preparing', name)
        datas = config['loader']()
        saver = config.get('saver', _save_as_tfrecord)
        for sub_name, data in datas.items():
            if sub_name == 'readme':
                filename = os.path.join(core.DATA_DIR, '%s-%s.txt' % (name, sub_name))
                with tf.io.gfile.GFile(filename, 'w') as f:
                    f.write(data)
            elif sub_name == 'files':
                for file_and_data in data:
                    path = os.path.join(core.DATA_DIR, file_and_data.filename)
                    with tf.io.gfile.GFile(path, "wb") as f:
                        f.write(file_and_data.data)
            else:
                saver(data, '%s-%s' % (name, sub_name))


if __name__ == '__main__':
    app.run(main)
