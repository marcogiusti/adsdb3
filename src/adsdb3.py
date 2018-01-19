# Copyright (c) 2018 Marco Giusti

import datetime
import decimal
import re
import struct
import time
import warnings
import weakref
from _ace import ffi, lib


__all__ = [
    'apilevel', 'threadsafety', 'paramstyle', 'connect', 'Warning', 'Error',
    'InterfaceError', 'DatabaseError', 'DataError', 'OperationalError',
    'IntegrityError', 'InternalError', 'ProgrammingError', 'NotSupportedError',
    'Date', 'Time', 'Timestamp', 'DateFromTicks', 'TimeFromTicks',
    'TimestampFromTicks', 'Binary', 'STRING', 'BINARY', 'NUMBER', 'DATETIME',
    'ROWID'
]


API_VERSION = 1
apilevel = '2.0'
threadsafety = 1
paramstyle = 'qmark'

_FORMATS = 'xxxdqQiIhHbBxxxxx'
_MIN_INT32 = -(2 ** 31)
_MAX_INT32 = 2 ** 31 - 1
_MIN_INT64 = -(2 ** 63)
_MAX_INT64 = 2 ** 63 - 1
_TIME_RE = re.compile(
    r'^'
    r'(?P<hour>\d{2})'
    r':'
    r'(?P<minute>\d{2})'
    r':'
    r'(?P<second>\d{2})'
    r'(?P<microsecond>\.\d+)?'
    r'(?: (?P<ampm>AM|PM))?'
    r'$'
)
_NATIVE_ERROR_RE = re.compile(r'NativeError\s+=\s+(?P<errno>\d+);')
_ref_bucket = weakref.WeakKeyDictionary()


ver = ffi.new('unsigned int[1]', [API_VERSION])
if not lib.ads_init(b'adsdb3', API_VERSION, ver):
    raise ImportError('Error initializing libace')
if ver[0] != API_VERSION:
    lib.ads_fini()
    raise ImportError(
        'Incompatible libace version %s. Required %s' % (ver[0], API_VERSION)
    )
del ver


class DBAPITypeObject:

    def __init__(self, *values):
        self.values = frozenset(values)

    def __eq__(self, other):
        if other in self.values:
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


STRING = DBAPITypeObject(
    lib.DT_VARCHAR,
    lib.DT_FIXCHAR,
    lib.DT_LONGVARCHAR,
    lib.DT_STRING,
    lib.DT_NSTRING,
    lib.DT_NFIXCHAR,
    lib.DT_NVARCHAR,
    lib.DT_LONGNVARCHAR
)
BINARY = DBAPITypeObject(
    lib.DT_BINARY,
    lib.DT_LONGBINARY
)
NUMBER = DBAPITypeObject(
    lib.DT_DOUBLE,
    lib.DT_FLOAT,
    lib.DT_DECIMAL,
    lib.DT_INT,
    lib.DT_SMALLINT,
    lib.DT_TINYINT,
    lib.DT_BIGINT,
    lib.DT_UNSINT,
    lib.DT_UNSSMALLINT,
    lib.DT_UNSBIGINT,
    lib.DT_BIT
)
DATETIME = DBAPITypeObject(
    lib.DT_DATE,
    lib.DT_TIME,
    lib.DT_TIMESTAMP
)
ROWID = DBAPITypeObject()
_UNICODE_FIELD = (
    lib.DT_NSTRING,
    lib.DT_NFIXCHAR,
    lib.DT_NVARCHAR,
    lib.DT_LONGNVARCHAR
)


class Warning(Exception):
    pass


class Error(Exception):
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):

    def __init__(self, msg, errno=-1):
        super().__init__(errno, msg)
        self.msg = msg
        self.errno = errno


class DataError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class InternalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


def _error(handler):
    buflength = lib.ADS_MAX_ERROR_LEN
    buf = ffi.new('char[]', buflength + 1)
    errno = lib.ads_error(handler, buf, buflength)
    if errno == 0:
        return 'internal error: success', 0
    msg = ffi.string(buf, buflength + 1).decode('ascii', 'ignore').rstrip()
    if errno == 7200:
        # because 7200 seems to be a generic error we look for a more specific
        # error code and we report that instead
        matchobj = _NATIVE_ERROR_RE.search(msg)
        if matchobj is not None:
            errno = int(matchobj.group('errno') or 0)
    return msg, errno


def _to_python(value, encoding):
    if value.is_null[0]:
        return None
    if value.type == lib.A_INVALID_TYPE:
        # XXX: Don't know what to do
        raise OperationalError('Invalid type')
    try:
        fmt = _FORMATS[value.type]
    except IndexError:
        raise OperationalError('Unknown data type %s' % (value.type)) from None
    if fmt != 'x':
        data = ffi.buffer(value.buffer, value.length[0])
        return struct.unpack(fmt, data)[0]
    data = ffi.unpack(value.buffer, value.length[0])
    if value.type == lib.A_BINARY:
        return data
    elif value.type == lib.A_STRING:
        # XXX: I need more infos how to handle encoding
        return data.decode(encoding)
    elif value.type == lib.A_NCHAR:
        return data.decode('utf-16')
    data = data.decode('ascii')
    if value.type == lib.A_DECIMAL:
        return decimal.Decimal(data)
    elif value.type == lib.A_DATE:
        return _date(data)
    elif value.type == lib.A_TIME:
        return _time(data)
    elif value.type == lib.A_TIMESTAMP:
        return _datetime(data)
    else:
        raise OperationalError('Invalid type {0}'.format(value.type))


def _date(s):
    if not s:
        return None
    return datetime.datetime.strptime(s, '%m/%d/%Y').date()


def _time(s):
    if not s:
        return None
    matchobj = _TIME_RE.match(s)
    if matchobj:
        hour = int(matchobj.group('hour'))
        if hour == 12:
            hour = 0
        if matchobj.group('ampm') == 'PM':
            hour += 12
        if matchobj.group('microsecond'):
            microsecond = int(float(matchobj.group('microsecond')) * 1000000)
        else:
            microsecond = 0
        return datetime.time(
            hour,
            int(matchobj.group('minute')),
            int(matchobj.group('second')),
            microsecond
        )
    else:
        raise OperationalError('Invalid time value %s' % (s, ))


def _datetime(s):
    if not s:
        return None
    if ' ' in s:
        sd, st = s.split(' ', 1)
        d = _date(sd)
        t = _time(st)
        return datetime.datetime(
            d.year,
            d.month,
            d.day,
            t.hour,
            t.minute,
            t.second,
            t.microsecond
        )
    else:
        return _date(s)


def _is_int32(value):
    return _MIN_INT32 <= value <= _MAX_INT32


def _is_int64(value):
    return _MIN_INT64 <= value <= _MAX_INT64


def _infer_type(param, value):
    if isinstance(value, int):
        if _is_int32(value):
            return lib.A_VAL32
        if _is_int64(value):
            return lib.A_VAL64
        else:
            raise DataError('Value out of range {}'.format(value))
    elif isinstance(value, float):
        return lib.A_DOUBLE
    elif isinstance(value, bytes):
        return lib.A_BINARY
    else:
        return lib.A_STRING


def _from_python(param, value, encoding):
    is_null = ffi.new('int *', value is None)
    param.value.is_null = is_null

    if is_null[0]:
        value = 0
    if param.value.type == lib.A_INVALID_TYPE:
        param.value.type = _infer_type(param, value)

    fmt = _FORMATS[param.value.type]
    if fmt == 'x':
        if isinstance(value, bytes):
            size = length = len(value)
        elif isinstance(value, str):
            param.value.type = lib.A_NCHAR
            value = value.encode('utf-16')
            size = length = len(value) + 2  # +2 for the BOM chars
        else:
            try:
                value = str(value).encode('ascii')
            except UnicodeEncodeError:
                raise DataError('Cannot convert value {}'.format(value))
            size = length = len(value)
    else:
        value = struct.pack(fmt, value)
        size = length = struct.calcsize(fmt)
    buf = ffi.new('char[]', value)
    param.value.buffer = buf
    param.value.buffer_size = size
    l = ffi.new('size_t[1]', [length])
    param.value.length = l
    _ref_bucket[param] = (is_null, buf, l)


def connect(connection_string=None, **kwds):
    if not isinstance(connection_string, str):
        connection_string = ';'.join('{}={}'.format(*i) for i in kwds.items())
    connection_string = connection_string.encode('ascii')
    handler = lib.ads_new_connection()
    if not handler:
        raise InternalError(*_error(None))
    return Connection(handler, connection_string)


class Connection:

    Warning = Warning
    Error = Error
    InterfaceError = InterfaceError
    DatabaseError = DatabaseError
    DataError = DataError
    OperationalError = OperationalError
    IntegrityError = IntegrityError
    InternalError = InternalError
    ProgrammingError = ProgrammingError
    NotSupportedError = NotSupportedError

    encoding = 'Windows-1252'

    def __init__(self, handler, connection_string):
        self._handler = handler
        self._finalizer = weakref.finalize(self, self._cleanup, handler)
        if not lib.ads_connect(handler, connection_string):
            raise OperationalError(*_error(handler))

    @classmethod
    def _cleanup(cls, handler):
        warnings.warn('Implicit connection cleanup', ResourceWarning)
        cls._close(handler)

    @classmethod
    def _close(cls, handler):
        lib.ads_rollback(handler)
        try:
            if not lib.ads_disconnect(handler):
                raise OperationalError(*_error(handler))
        finally:
            lib.ads_free_connection(handler)

    def close(self):
        if self._finalizer.detach():
            self._close(self._handler)
            self._handler = None

    def _complain_if_closed(self):
        if self._handler is None:
            raise InterfaceError('connection closed')

    def _trans_raise(self):
        msg, errno = _error(self._handler)
        if errno != lib.AE_TRANS_OUT_OF_SEQUENCE:
            # Cit. the documentation:
            # > The error code AE_TRANS_OUT_OF_SEQUENCE will be
            # > returned if a specific connection handle is given to
            # > AdsCommitTransaction and that connection is not in a
            # > transaction
            # Because we don't want to raise an exception in such
            # case, ignore it
            raise OperationalError(msg, errno)

    def _rollback_on_close(self):
        if self._handler is not None:
            if not lib.ads_rollback(self._handler):
                self._trans_raise()

    def commit(self):
        self._complain_if_closed()
        if not lib.ads_commit(self._handler):
            self._trans_raise()

    def rollback(self):
        self._complain_if_closed()
        if not lib.ads_rollback(self._handler):
            self._trans_raise()

    def cursor(self):
        self._complain_if_closed()
        return Cursor(self)


class Cursor:

    arraysize = 1
    _closed = False
    _stmt = None
    _description = None
    _rowcount = -1

    @property
    def connection(self):
        warnings.warn('DB-API extension cursor.connection used')
        self._complain_if_closed()
        return self._connection

    @property
    def description(self):
        self._complain_if_closed()
        return self._description

    @property
    def rowcount(self):
        self._complain_if_closed()
        return self._rowcount

    # @property
    # def encoding(self):
    #     warnings.warn('DB-API extension cursor.encoding used')
    #     return self._connection.encoding

    def __init__(self, connection):
        self._connection = connection

    def __enter__(self):
        self._complain_if_closed()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self._connection.commit()
        else:
            self._connection.rollback()

    def __iter__(self):
        warnings.warn('DB-API extension cursor.__iter__() used')
        self._complain_if_closed()
        return self

    def __next__(self):
        warnings.warn('DB-API extension cursor.__next__() used')
        self._complain_if_closed()
        self._complain_if_noset()
        return next(self._stmt.iter_rows())

    def close(self):
        if not self._closed:
            try:
                self._connection._rollback_on_close()
            finally:
                self._reset()
                self._closed = True

    def _reset(self):
        if self._stmt is not None:
            self._stmt.free()
        self._stmt = None
        self._description = None
        self._rowcount = -1

    def _prepare_statement(self, operation):
        handler = self._connection._handler
        # since ACE needs 2 NULL chars for utf-16
        operation = operation.encode('utf-16') + b'\x00'
        stmt = lib.ads_prepare(handler, operation, True)
        if not stmt:
            raise DatabaseError(*_error(handler))
        return _Statement(stmt, handler, self._connection.encoding)

    def _complain_if_closed(self):
        if self._closed:
            raise InterfaceError('cursor closed')
        self._connection._complain_if_closed()

    def _complain_if_noset(self):
        if self._stmt is None:
            raise InterfaceError('No operation issued')
        if self._description is None:
            raise InterfaceError('No results to fetch')

    def callproc(self, procname, parameters=()):
        operation = 'EXECUTE PROCEDURE {procname}({args})'.format(
            procname=procname,
            args=','.join(['?'] * len(parameters))
        )
        return self.execute(operation, parameters)

    def execute(self, operation, parameters=()):
        self._complain_if_closed()
        self._reset()
        self._stmt = stmt = self._prepare_statement(operation)
        stmt.bind_params(parameters)
        stmt.execute()
        try:
            self._description = stmt.columns_info()
            if self._description is None:
                self._rowcount = stmt.affected_rows()
            else:
                self._rowcount = stmt.num_rows()
        except:
            self._description = None
            self._rowcount = -1
            raise

    def executemany(self, operation, seq_of_paramenters):
        self._complain_if_closed()
        rowcount_s = False
        rowcount = 0
        for parameters in seq_of_paramenters:
            self.execute(operation, parameters)
            if self._rowcount > 0:
                rowcount += self._rowcount
                rowcount_s = True
        if rowcount_s:
            self._rowcount = rowcount

    def _fetch(self, size):
        self._complain_if_closed()
        self._complain_if_noset()
        if size == 'all':
            return list(self._stmt.iter_rows())
        elif size == 'one':
            return next(self._stmt.iter_rows(), None)
        else:
            return [row for i, row in zip(range(size), self._stmt.iter_rows())]

    def fetchone(self):
        return self._fetch('one')

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize
        return self._fetch(size)

    def fetchall(self):
        return self._fetch('all')

    def setinputsizes(self, sizes):
        pass

    def setoutputsize(self, size, column=None):
        pass


class _Statement:

    def __init__(self, stmt, handler, encoding):
        self.stmt = stmt
        self._finalizer = weakref.finalize(self, self._cleanup, stmt)
        self.handler = handler
        self.encoding = encoding

    @classmethod
    def _cleanup(cls, stmt):
        warnings.warn('Implicit statement cleanup', ResourceWarning)
        lib.ads_free_stmt(stmt)

    def free(self):
        if self._finalizer.detach():
            lib.ads_free_stmt(self.stmt)

    def num_params(self):
        ret = lib.ads_num_params(self.stmt)
        if ret == -1:
            raise DatabaseError(*_error(self.handler))
        return ret

    def bind_params(self, params):
        for i, param in enumerate(params[:self.num_params()]):
            self.bind(i, param)

    def bind(self, i, value):
        param = ffi.new('struct a_ads_bind_param *')
        if not lib.ads_describe_bind_param(self.stmt, i, param):
            raise DatabaseError(*_error(self.handler))
        _from_python(param, value, self.encoding)
        if not lib.ads_bind_param(self.stmt, i, param):
            raise DatabaseError(*_error(self.handler))

    def execute(self):
        if not lib.ads_execute(self.stmt):
            raise DatabaseError(*_error(self.handler))

    def fetch_next(self):
        return lib.ads_fetch_next(self.stmt)

    def num_cols(self):
        n = lib.ads_num_cols(self.stmt)
        if n < 0:
            raise DatabaseError(*_error(self.handler))
        return n

    def num_rows(self):
        n = lib.ads_num_rows(self.stmt)
        return -1 if n < 0 else n

    def affected_rows(self):
        n = lib.ads_affected_rows(self.stmt)
        return -1 if n < 0 else n

    def column_info(self, i):
        info = ffi.new('struct a_ads_column_info *')
        lib.ads_get_column_info(self.stmt, i, info)
        if info.native_type in _UNICODE_FIELD:
            # Precision and size here are in bytes, so convert it to chars
            # for unicode fields
            info.precision = info.precision // 2
            info.max_size = info.max_size // 2
        return (
            ffi.string(info.name).decode('ascii', 'ignore'),
            info.native_type,
            None,
            info.max_size,
            info.precision,
            info.scale,
            info.nullable
        )

    def columns_info(self):
        n = self.num_cols()
        if n > 0:
            return tuple(self.column_info(i) for i in range(n))
        return None

    def iter_rows(self):
        while lib.ads_fetch_next(self.stmt):
            yield tuple(self.iter_columns())

    def iter_columns(self):
        data_value = ffi.new('struct a_ads_data_value *')
        for i in range(self.num_cols()):
            if not lib.ads_get_column(self.stmt, i, data_value):
                raise DatabaseError(*_error(self.handler))
            yield _to_python(data_value, self.encoding)


def Binary(s):
    # TODO: do the conversion
    return s


def Date(year, month, day):
    return '{:4}/{:2}/{:2}'.format(year, month, day)


def Time(hour, minute, second):
    return '{:2}:{:2}:{:2}'.format(hour, minute, second)


def Timestamp(year, month, day, hour, minute, second):
    return '{:4}/{:2}/{:2} {:2}:{:2}:{:2}'.format(
        year, month, day, hour, minute, second
    )


def DateFromTicks(ticks):
    return Date(*time.localtime(ticks)[:3])


def TimeFromTicks(ticks):
    return Time(*time.localtime(ticks)[3:6])


def TimestampFromTicks(ticks):
    return Timestamp(*time.localtime(ticks)[:6])
