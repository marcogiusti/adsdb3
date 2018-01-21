# Copyright (c) 2018 Marco Giusti

import warnings

import dbapi20
import adsdb3
from adsdb3_test_utils import ConnectMixin


class TestADS_DBAPI20(ConnectMixin, dbapi20.DatabaseAPI20Test):

    driver = adsdb3
    lower_func = None

    @classmethod
    def setUpClass(cls):
        cls.catcher = warnings.catch_warnings()
        cls.catcher.__enter__()
        warnings.filterwarnings(
            'ignore',
            'Implicit statement cleanup',
            ResourceWarning,
            'adsdb3'
        )
        warnings.filterwarnings(
            'ignore',
            'Please use assertTrue instead',
            DeprecationWarning,
            'dbapi20'
        )

    @classmethod
    def tearDownClass(cls):
        cls.catcher.__exit__(None, None, None)

    def test_setoutputsize(self):
        # not implemented
        pass

    def test_nextset(self):
        # not implemented
        pass
