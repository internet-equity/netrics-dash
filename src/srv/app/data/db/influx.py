import itertools

from influxdb import InfluxDBClient

from app import config


class Client(InfluxDBClient):

    bind_params_base = (
        ('install_id', config('INSTALL_ID')),
    )

    #
    # set useful defaults
    #
    def __init__(self,
                 # overridden defaults:
                 host=config('INFLUXDB_SERVER'),        # 'localhost'
                 port=config('INFLUXDB_PORT'),          # 8086
                 username=config('INFLUXDB_USERNAME'),  # 'root'
                 password=config('INFLUXDB_PASSWORD'),  # 'root'
                 database=config('INFLUXDB_DATABASE'),  # None
                 ssl=True,                              # False
                 verify_ssl=True,                       # False

                 # as inherited:
                 **kwargs,
                 ):
        """Construct a new InfluxDBClient object."""
        super().__init__(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            ssl=ssl,
            verify_ssl=verify_ssl,
            **kwargs,
        )

    #
    # set useful defaults
    #
    def query(self, query, params=None, bind_params=None, **kwargs):
        """Send a query to InfluxDB."""
        return super().query(
            query,
            params,
            # set default bind_params
            bind_params=dict(self.bind_params_base, **(bind_params or {})),
            **kwargs,
        )

    #
    # fix broken __enter__
    #
    # (broken in 5.3.1 & fixed in master)
    #
    def __enter__(self):
        """Enter function as used by context manager."""
        return self


def get_point(response, *args):
    for values in get_points(response, *args, limit=1):
        yield next(iter(values), None)


def get_points(response, *args, limit=None):
    if not args:
        raise TypeError('at least one value name required')
    elif isinstance(args[-1], str):
        (names, round_to) = (args, None)
    else:
        (*names, round_to) = args

    points = itertools.islice(response.get_points(), limit)

    for (name, it) in zip(names, itertools.tee(points, len(names))):
        values = (point[name] for point in it)
        yield [
            value if round_to is None or value is None else round(value, round_to)
            for value in values
        ]
