import unittest
import lsst.utils.tests


class UtilsBinaryTester(lsst.utils.tests.ExecutablesTestCase):
    pass

EXECUTABLES = ("binary1", "binary2")
UtilsBinaryTester.create_executable_tests(__file__, EXECUTABLES)

if __name__ == "__main__":
    unittest.main()
