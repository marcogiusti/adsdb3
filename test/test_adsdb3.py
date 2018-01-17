# Copyright (c) 2018 Marco Giusti

from contextlib import closing
import decimal
import datetime
import unittest
import weakref

from hypothesis import given
from hypothesis.strategies import integers

import adsdb3
from adsdb3 import ffi, lib
from adsdb3_test_utils import ConnectMixin


_ref_bucket = weakref.WeakKeyDictionary()


class TestToPython(unittest.TestCase):

    encoding = 'Windows-1252'

    def test_invalid_type(self):
        value = ffi.new('struct a_ads_data_value *')
        is_null = ffi.new('int *', 0)
        value.is_null = is_null
        value.type = lib.A_INVALID_TYPE
        self.assertRaises(
            adsdb3.OperationalError,
            adsdb3._to_python,
            value,
            self.encoding
        )

    def _new_data_value(self, typ, buf, length, is_null=0):
        value = ffi.new('struct a_ads_data_value *')
        _is_null = ffi.new('int *', is_null)
        value.is_null = _is_null
        value.type = typ
        _buf = ffi.new('char[]', buf)
        value.buffer = _buf
        _length = ffi.new('size_t *', length)
        value.length = _length
        _ref_bucket[value] = _is_null, _buf, _length
        return value

    def _test_type(self, type, value, buf, length):
        datavalue = self._new_data_value(type, buf, length)
        self.assertEqual(adsdb3._to_python(datavalue, self.encoding), value)

    def test_val64_type(self):
        self._test_type(
            lib.A_VAL64,
            6510615555426900570,
            b'\x5a\x5a\x5a\x5a\x5a\x5a\x5a\x5a',
            8
        )

    def test_uval64_type(self):
        self._test_type(
            lib.A_UVAL64,
            11936128518282651045,
            b'\xa5\xa5\xa5\xa5\xa5\xa5\xa5\xa5',
            8
        )

    def test_val32_type(self):
        self._test_type(lib.A_VAL32, 1515870810, b'\x5a\x5a\x5a\x5a', 4)

    def test_uval32_type(self):
        self._test_type(lib.A_UVAL32, 2779096485, b'\xa5\xa5\xa5\xa5', 4)

    def test_val16_type(self):
        self._test_type(lib.A_VAL16, 23130, b'\x5a\x5a', 2)

    def test_uval16_type(self):
        self._test_type(lib.A_UVAL16, 42405, b'\xa5\xa5', 2)

    def test_val8_type(self):
        self._test_type(lib.A_VAL8, 5, b'\x05', 1)

    def test_uval8_type(self):
        self._test_type(lib.A_UVAL8, 10, b'\x0a', 1)

    def test_binary_type(self):
        binary = b'ciao ciao'
        self._test_type(lib.A_BINARY, binary, binary, len(binary))

    def test_string_type(self):
        buf = b'\xc7a peut pas faire de mal'
        res = 'Ça peut pas faire de mal'
        self._test_type(lib.A_STRING, res, buf, len(buf))

    def test_double_type(self):
        buf = b'\x9a\x99\x99\x99\x99\x99\xf1?'
        self._test_type(lib.A_DOUBLE, 1.1, buf, 8)

    def test_nchar_type(self):
        buf = (
            b'\xc7\x00a\x00 \x00p\x00e\x00u\x00t\x00 \x00p\x00a\x00s\x00 '
            b'\x00f\x00a\x00i\x00r\x00e\x00 \x00d\x00e\x00 \x00m\x00a\x00l\x00'
        )
        res = 'Ça peut pas faire de mal'
        self._test_type(lib.A_NCHAR, res, buf, len(buf))

    def test_decimal_type(self):
        buf = b'1.1'
        self._test_type(lib.A_DECIMAL, decimal.Decimal('1.1'), buf, len(buf))

    def test_date_type(self):
        buf = b'12/19/2015'
        self._test_type(lib.A_DATE, datetime.date(2015, 12, 19), buf, len(buf))

    def test_time_type(self):
        buf = b'18:10:00'
        self._test_type(lib.A_TIME, datetime.time(18, 10), buf, len(buf))

    def test_datetime_type(self):
        buf = b'12/19/2015 18:10:00'
        self._test_type(
            lib.A_TIMESTAMP,
            datetime.datetime(2015, 12, 19, 18, 10, 00),
            buf,
            len(buf)
        )


def is_int16(i):
    return -2**15 <= i <= 2**15 - 1


def is_int32(i):
    return -2**31 <= i <= 2**31 - 1


def is_int64(i):
    return -2**63 <= i <= 2**63 - 1


class TestField(ConnectMixin):

    ddl = None
    xddl = 'DROP TABLE {table_prefix}booze'
    table_prefix = 'adsdb3test_'

    def setUp(self):
        ddl = self.ddl.format(table_prefix=self.table_prefix)
        xddl = self.xddl.format(table_prefix=self.table_prefix)
        connection = self.connect()
        cursor = connection.cursor()
        self.addCleanup(cursor.close)
        cursor.execute(ddl)
        self.addCleanup(cursor.execute, xddl)
        self.connection = connection

    def _insert(self, connection, values):
        stmt = 'INSERT INTO {}booze VALUES(?)'.format(self.table_prefix)
        with closing(connection.cursor()) as cursor:
            cursor.execute(stmt, values)


class TestInteger(TestField, unittest.TestCase):

    ddl = '''
    CREATE TABLE {table_prefix}booze (
        int_field INTEGER
    )
    '''

    @given(i=integers())
    def test_integer(self, i):
        try:
            self._insert(self.connection, [i])
        except adsdb3.DataError:
            if is_int64(i):
                raise
        except adsdb3.DatabaseError as exc:
            if not (exc.errno == lib.AE_VALUE_OVERFLOW and not is_int32(i)):
                raise

    @given(i=integers())
    def test_str(self, i):
        try:
            self._insert(self.connection, [str(i)])
        except adsdb3.DataError:
            if is_int64(i):
                raise
        except adsdb3.DatabaseError as exc:
            if not (exc.errno == lib.AE_VALUE_OVERFLOW and not is_int32(i)):
                raise


class TestShort(TestField, unittest.TestCase):

    ddl = '''
    CREATE TABLE {table_prefix}booze (
        short_field SHORT
    )
    '''

    @given(s=integers())
    def test_short_integer(self, s):
        try:
            self._insert(self.connection, [s])
        except adsdb3.DataError:
            if is_int64(s):
                raise
        except adsdb3.DatabaseError as exc:
            if not (exc.errno == lib.AE_VALUE_OVERFLOW and not is_int16(s)):
                raise

    @given(s=integers())
    def test_str(self, s):
        try:
            self._insert(self.connection, [str(s)])
        except adsdb3.DataError:
            if is_int64(s):
                raise
        except adsdb3.DatabaseError as exc:
            if not (exc.errno == lib.AE_VALUE_OVERFLOW and not is_int16(s)):
                raise


class TestFromPython(ConnectMixin, unittest.TestCase):

    ddl = '''
    CREATE TABLE {}booze (
        b BLOB,
        c CHAR(10),
        vc VARCHAR(10),
        d DOUBLE,
        i INTEGER,
        s SHORT,
        nc NCHAR(24),
        vnc NVARCHAR(60),
        -- n NUMERIC,
        da DATE,
        t TIME,
        ts TIMESTAMP,
        l LOGICAL
    )
    '''
    xddl = 'drop table {}booze'
    table_prefix = 'adsdb3test_'

    def setUp(self):
        ddl = self.ddl.format(self.table_prefix)
        xddl = self.xddl.format(self.table_prefix)
        connection = self.connect()
        cursor = connection.cursor()
        self.addCleanup(cursor.close)
        cursor.execute(ddl)
        self.addCleanup(cursor.execute, xddl)
        self.connection = connection

    def _insert(self, cursor, values):
        stmt = '''
        INSERT INTO {}booze
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''.format(self.table_prefix)
        cursor.execute(stmt, values)

    def _select_all(self, cursor):
        stmt = 'SELECT * FROM {}booze'.format(self.table_prefix)
        cursor.execute(stmt)
        return cursor.fetchone()

    def test_insert_null(self):
        with closing(self.connection.cursor()) as cursor:
            values = [None] * 12
            self._insert(cursor, values)

    def _insert_get_value(self, index, value, expected):
        with closing(self.connection.cursor()) as cursor:
            values = [None] * 12
            values[index] = value
            self._insert(cursor, values)
            new = self._select_all(cursor)[index]
            self.assertEqual(new, expected)

    def _test_date(self, value, expected):
        self._insert_get_value(8, value, expected)

    def test_date1(self):
        date = datetime.date.today()
        self._test_date(format(date, '%Y-%m-%d'), date)

    def test_date2(self):
        date = datetime.date.today()
        self._test_date(date, date)

    def test_time1(self):
        time = datetime.datetime.now().time().replace(microsecond=0)
        self._insert_get_value(9, time, time)

    def test_time2(self):
        time = datetime.datetime.now().time().replace(microsecond=0)
        self._insert_get_value(9, format(time, '%H:%M:%S'), time)

    def test_datetime1(self):
        dt = datetime.datetime.now().replace(microsecond=0)
        self._insert_get_value(10, format(dt, '%Y-%m-%d %H:%M:%S'), dt)

    def test_datetime2(self):
        dt = datetime.datetime.now().replace(microsecond=0)
        self._insert_get_value(10, dt, dt)

    def test_binary1(self):
        value = b'\x55\xAA'
        self._insert_get_value(0, value, value)

    @unittest.expectedFailure
    def test_binary2(self):
        value = '\x55\xAA'
        self._insert_get_value(0, value, value)

    def test_double(self):
        value = 1.1
        self._insert_get_value(3, value, value)

    def test_nchar(self):
        value = 'Ça peux pas faire de mal'
        self._insert_get_value(6, value, value)

    def test_nvarchar(self):
        value = 'Ça peux pas faire de mal'
        self._insert_get_value(7, value, value)
