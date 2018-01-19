# Copyright (c) 2018 Marco Giusti

import os
from contextlib import closing
import unittest

import adsdb3


data_source = os.environ.get('ADSDB3_DATASOURCE')
connection_string = os.environ.get('ADSDB3_CONNECTION_STRING')
should_skip = data_source is None and connection_string is None


@unittest.skipIf(should_skip, 'Do not know how to connect to the DB')
class ConnectMixin:

    if connection_string is not None:
        connect_args = connection_string,
        connect_kw_args = {}
    elif data_source is not None:
        connect_args = ()
        connect_kw_args = {
            'CharType': 'ANSI',
            'CommType': 'TCP_IP',
            'DataSource': data_source,
            'Exact': False,
            'FIPS': False,
            'ReadOnly': True,
            'ServerType': 2,
            'TrimTrailingSpaces': True
        }
    else:
        connect_args = ()
        connect_kw_args = {}

    def connect(self):
        connection = adsdb3.connect(*self.connect_args, **self.connect_kw_args)
        self.addCleanup(connection.close)
        return connection

    def _connect(self):
        try:
            adsdb3.connect
        except AttributeError:
            self.fail("No connect method found in self.driver module")
        else:
            return self.connect()


class DDLMixin(ConnectMixin):

    ddl = None
    xddl = None
    prefix = 'adsdb3test_'

    def setUp(self):
        super().setUp()
        ddl = self.ddl.format(prefix=self.prefix)
        connection = self.connect()
        with closing(connection.cursor()) as cursor:
            cursor.execute(ddl)
        if self.xddl is not None:
            xddl = self.xddl.format(prefix=self.prefix)
            self.addCleanup(self._do_xddl, connection, xddl)
        self.connection = connection

    @staticmethod
    def _do_xddl(connection, xddl):
        with closing(connection.cursor()) as cursor:
            cursor.execute(xddl)
