"""Interface to read operations on sets of Netrics data files."""
import abc
import collections
import functools
import heapq
import json
import numbers
import pathlib
import statistics
import time

from app import config


ONE_WEEK_S = 60 * 60 * 24 * 7


def path_or_none(value):
    return value if value is None else pathlib.Path(value)


DATAFILE_PENDING = config('DATAFILE_PENDING', default=None, cast=path_or_none)
DATAFILE_ARCHIVE = config('DATAFILE_ARCHIVE', default=None, cast=path_or_none)

DATA_PATHS = (
    ((DATAFILE_PENDING,) if DATAFILE_PENDING else ()) +
    ((DATAFILE_ARCHIVE,) if DATAFILE_ARCHIVE else ())
)

DATAFILE_LIMIT = DATA_CACHE_SIZE = 500

DATAFILE_PREFIX = 'Measurements'

META_PREFIX = 'Meta'


def get_multikey(multikey, values):
    value = values
    for key in multikey.split('.'):
        value = value[key]
    return value


class DataFileBank:
    """Interface to read operations on sets of Netrics data files."""

    def __init__(self,
                 prefix=DATAFILE_PREFIX,
                 file_limit=DATAFILE_LIMIT,
                 dirs=DATA_PATHS,
                 round_to=None,
                 flat=False,
                 meta_prefix=META_PREFIX):
        self.prefix = prefix
        self.file_limit = file_limit
        self.dirs = dirs
        self.round_to = round_to
        self.flat = flat
        self.meta_prefix=meta_prefix

    def get_points(self, *ops, **named_ops):
        op_stack = dict(((str(op), op) for op in ops), **named_ops)
        points = dict.fromkeys(op_stack)

        if self.flat and len(points) > 1:
            raise ValueError("cannot flatten multiple keys")

        path_dirs = iter(self.dirs)

        paths_counted = iter(())
        path_count = 0

        while op_stack and path_count < self.file_limit:
            try:
                (path_count, path) = next(paths_counted)
            except StopIteration:
                # path directory exhausted:
                # initialize (next) path directory
                try:
                    path_dir = next(path_dirs)
                except StopIteration:
                    break

                path_remainder = self.file_limit - path_count
                paths_sorted = heapq.nlargest(path_remainder, path_dir.iterdir())
                paths_counted = enumerate(paths_sorted, 1 + path_count)
                continue

            full_data = self.get_json(path)

            if self.prefix:
                try:
                    data = get_multikey(self.prefix, full_data)
                except KeyError:
                    continue
            else:
                data = full_data

            for (write_key, aggregator) in tuple(op_stack.items()):
                try:
                    points[write_key] = aggregator(
                        data,
                        points[write_key],
                        {
                            'data': full_data,
                            'points': points,
                            'write_key': write_key,
                            'path_count': path_count,
                            'file_limit': self.file_limit,
                            'last': path_count + 1 == self.file_limit,
                            'meta_prefix': self.meta_prefix,
                            'flat': self.flat,
                        },
                    )
                except aggregator.stop_reduce as stop_reduce:
                    points[write_key] = self.round_value(stop_reduce.value)
                    del op_stack[write_key]

                #
                # note: the following is left for educational purposes only
                #
                # this method originally merely retrieved the last value of the key's time series;
                # hence, the below performed the same as the current DataFileAggregator: Last
                #
                # key_data = data
                #
                # try:
                #     for key in read_key.split('.'):
                #         key_data = key_data[key]
                # except KeyError:
                #     pass
                # else:
                #     del key_stack[write_key]
                #     points[write_key] = self.round_value(key_data)

        # DEBUG: points['_path_count'] = path_count

        if self.flat:
            (points,) = points.values()

        return points

    #
    # In testing against an HTTP endpoint whose query required ~500 files,
    # an LRU cache of the same size added a lag of ~10% to the initial request,
    # and reduced subsequent requests' time by an order of magnitude (~90%).
    #
    # However: cache size should be ensured to be at least as large as the file
    # limit, to ensure cache functionality.
    #
    @staticmethod
    @functools.lru_cache(maxsize=DATA_CACHE_SIZE)
    def get_json(path):
        with path.open() as fd:
            return json.load(fd)

    def round_value(self, value):
        if self.round_to is not None:
            if isinstance(value, numbers.Number):
                return round(value, self.round_to)
            elif isinstance(value, list):
                return [self.round_value(value0) for value0 in value]
            elif isinstance(value, tuple):
                return tuple(self.round_value(value0) for value0 in value)
            elif isinstance(value, dict):
                return {key: self.round_value(value0) for (key, value0) in value.items()}

        return value


class FlatFileBank(DataFileBank):

    def __init__(self, **kwargs):
        if 'flat' in kwargs:
            raise TypeError("'flat' may not be specified to FlatFileBank()")

        super().__init__(flat=True, **kwargs)

    def get_columns(self, read_key, age_s, *, decorate=None, reverse=False):
        points = self.get_points(
            Multi(read_key, age_s, decorate=decorate, reverse=reverse)
        )

        (data_comp, meta) = zip(*points) if decorate else (points, None)

        if isinstance(read_key, str):
            return data_comp if meta is None else (data_comp, meta)

        data = tuple(zip(*data_comp))

        return data if meta is None else data + (meta,)


def get_points(*ops, **named_ops):
    file_bank = DataFileBank(round_to=1)
    return file_bank.get_points(*ops, **named_ops)


class StopReduce(Exception):
    """Raised to indicate completion and to share final result."""

    def __init__(self, value):
        super().__init__(value)
        self.value = value


class DataFileAggregator(abc.ABC):

    stop_reduce = StopReduce

    def __init__(self, read_key, *, decorate=None):
        self.read_key = read_key
        self.decorations = decorate

    @property
    def read_keys(self):
        return (self.read_key,) if isinstance(self.read_key, str) else self.read_key

    def get_multikey(self, values):
        results = []

        for (key_count, read_key) in enumerate(self.read_keys, 1):
            results.append(get_multikey(read_key, values))

        return results[0] if key_count == 1 else results

    def decorate(self, value, context):
        if self.decorations:
            if isinstance(self.decorations, str):
                decorations = (self.decorations,)
            else:
                decorations = self.decorations

            data = context['data']
            data_meta = data[context['meta_prefix']]

            value_meta = [data_meta.get(meta_key) for meta_key in decorations]

            if context['flat']:
                value = (
                    value,
                    value_meta[0] if isinstance(self.decorations, str) else value_meta,
                )
            else:
                value = {
                    'Measurement': value,
                    'Meta': dict(zip(self.decorations, value_meta)),
                }

        return value

    def __str__(self):
        return '__'.join(self.read_keys)

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ', '.join(f'{key}={value!r}' for (key, value) in self.__dict__.items()),
        )

    @abc.abstractmethod
    def __call__(self, current_values, current_result, context):
        pass


class Last(DataFileAggregator):

    def __call__(self, current_values, _current_result, context):
        try:
            value = self.get_multikey(current_values)
        except KeyError:
            return None

        raise self.stop_reduce(self.decorate(value, context))


class Multi(DataFileAggregator):

    def __init__(self, read_key, age_s, *, decorate=None, reverse=False):
        super().__init__(read_key, decorate=decorate)
        self.age_s = age_s
        self.reverse = reverse

    def __call__(self, current_values, collected, context):
        if collected is None:
            collected = collections.deque()

        data = context['data']
        data_meta = data[context['meta_prefix']]
        timestamp = data_meta['Time']
        if time.time() - timestamp >= self.age_s:
            raise self.make_stop(collected)

        try:
            current_value = self.get_multikey(current_values)
        except KeyError:
            pass
        else:
            decorated = self.decorate(current_value, context)

            if self.reverse:
                collected.appendleft(decorated)
            else:
                collected.append(decorated)

        if context['last']:
            raise self.make_stop(collected)

        return collected

    def make_stop(self, values):
        result = self.finalize(values)
        return self.stop_reduce(result)

    def finalize(self, values):
        return list(values)


class StdDev(Multi):

    def __init__(self, *args, **kwargs):
        if 'decorate' in kwargs:
            raise TypeError("'decorate' is an invalid keyword argument for StdDev()")

        super().__init__(*args, **kwargs)

    def finalize(self, values):
        try:
            return statistics.stdev(values)
        except statistics.StatisticsError:
            return None
