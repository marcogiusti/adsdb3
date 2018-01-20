# Copyright (c) 2018 Marco Giusti

import unittest
from _ace import ffi, lib


class TestACE(unittest.TestCase):

    def test_init(self):
        ver = ffi.new('unsigned int[1]', [1])
        try:
            self.assertEqual(lib.ads_init(b'test', 1, ver), 1)
        finally:
            lib.ads_fini()

    def test_new_connection(self):
        handler = lib.ads_new_connection()
        if handler:
            self.addCleanup(lib.ads_free_connection, handler)
        self.assertIsNotNone(handler)

    def test_free_connection_null(self):
        lib.ads_free_connection(ffi.NULL)

    def test_connect(self):
        handler = lib.ads_new_connection()
        if handler:
            self.addCleanup(lib.ads_free_connection, handler)
        rc = lib.ads_connect(handler, b'')
        self.addCleanup(lib.ads_disconnect, handler)
        self.assertEqual(rc, 0)

    def test_disconnect(self):
        handler = lib.ads_new_connection()
        if handler:
            self.addCleanup(lib.ads_free_connection, handler)
        self.assertIsNotNone(handler)
        self.assertEqual(lib.ads_disconnect(handler), 1)

    def test_disconnect_null(self):
        self.assertEqual(lib.ads_disconnect(ffi.NULL), 0)

    def test_disconnect_twice(self):
        handler = lib.ads_new_connection()
        if handler:
            self.addCleanup(lib.ads_free_connection, handler)
        self.assertIsNotNone(handler)
        self.assertEqual(lib.ads_disconnect(handler), 1)
        self.assertEqual(lib.ads_disconnect(handler), 1)

    def test_commit_null(self):
        self.assertEqual(lib.ads_commit(ffi.NULL), 0)

    def test_rollback_null(self):
        self.assertEqual(lib.ads_rollback(ffi.NULL), 0)

    def test_free_stmt_null(self):
        lib.ads_free_stmt(ffi.NULL)

    def test_fini_not_initialized(self):
        lib.ads_fini()

    def test_num_params_null(self):
        self.assertEqual(lib.ads_num_params(ffi.NULL), 0)


if __name__ == '__main__':
    unittest.main()
