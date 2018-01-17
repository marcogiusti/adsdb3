# Copyright (c) 2018 Marco Giusti

import dbapi20
import adsdb3
from adsdb3_test_utils import ConnectMixin


class TestADS_DBAPI20(ConnectMixin, dbapi20.DatabaseAPI20Test):

    driver = adsdb3
    lower_func = None

    def test_setoutputsize(self):
        # not implemented
        pass

    def test_nextset(self):
        # not implemented
        pass
