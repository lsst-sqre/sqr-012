..
  Content of technical report.

  See http://docs.lsst.codes/en/latest/development/docs/rst_styleguide.html
  for a guide to reStructuredText writing.

  Do not put the title, authors or other metadata in this document;
  those are automatically added.

  Use the following syntax for sections:

  Sections
  ========

  and

  Subsections
  -----------

  and

  Subsubsections
  ^^^^^^^^^^^^^^

  To add images, add the image file (png, svg or jpeg preferred) to the
  _static/ directory. The reST syntax for adding the image is

  .. figure:: /_static/filename.ext
     :name: fig-label
     :target: http://target.link/url

     Caption text.

   Run: ``make html`` and ``open _build/html/index.html`` to preview your work.
   See the README at https://github.com/lsst-sqre/lsst-report-bootstrap or
   this repo's README for more info.

   Feel free to delete this instructional comment.

:tocdepth: 1

The standard for `Python unit testing in LSST <http://developer.lsst.io/en/latest/coding/unit_test_policy.html>`_ is to use the ``unittest`` package.
LSST unit tests do not currently use the builtin ``unittest`` test discovery mechanism but instead the convention is to specify a list of explicit test classes by specifying a ``suite`` using the following boilerplate:

.. code-block:: python

   import lsst.utils.tests as tests

   <Test classes here subclasses of lsst.utils.tests.TestCase or unittest.TestCase>

   def suite():
       """Returns a suite containing all the test cases in this module."""
       tests.init()

       suites = []
       suites += unittest.makeSuite(FootprintSetTestCase)
       suites += unittest.makeSuite(PeaksInFootprintsTestCase)
       suites += unittest.makeSuite(tests.MemoryTestCase)
       return unittest.TestSuite(suites)

   def run(shouldExit=False):
       """Run the tests"""
       tests.run(suite(), shouldExit)

   if __name__ == "__main__":
       run(True)

Tests are set up like this to allow tests to be disabled by commenting out a single line, and also to allow the memory test to be included in every test file.
The memory test case is used to check for memory leaks in the C++ code and the ``tests.init()`` call is there to initialize the memory tester.
The ``run()`` method ensures that tests can exit with bad exit status if they fail, making it possible for ``sconsUtils`` to determine whether a particular test file passed or failed.

``sconsUtils`` testing works as follows: the ``tests`` directory is scanned looking for executable binaries and Python scripts; binaries are executed directly and Python scripts are executed using the ``python`` binary in the path; the exit status from this call determines whether the test passes or fails; the output from the tests is redirected to a file in a ``.tests`` subdirectory using the test name as the name of the output file and if the test failed ``.failed`` is appended to the filename; if ``scons`` finds any ``.failed`` files the ``test`` target itself fails and ``scons`` aborts the build.

Test Runners
============

Whilst ``unittest`` provides a reasonable environment for writing unit tests it does not make it easy for the software running the tests to obtain pass/fail/skip statistics when they are run, or report the duration of individual tests.
To do this a test runner environment is required such as `nose <https://github.com/nose-devs/nose>`_ or `pytest <http://pytest.org>`_.

Following the lead of `Astropy <http://www.astropy.org>`_ LSST is migrating away from a simple exit status approach to test running and switching to use pytest.
Pytest provides a very flexible testing environment and is much simpler to use than ``unittest`` itself.
At this time we are not proposing that ``unittest`` be dropped to make use of these testing simplifications and new tests should not be written relying solely on pytest.
We are switching to using pytest as the test runner.

Pytest can use the standard ``unittest`` test discovery mechanism which results in the ``suite`` boilerplate described above being bypassed when the test file is executed via ``py.test``.
The LSST test files must therefore be vetted to ensure that the tests function with automated test discovery and result in all tests being executed.

Supporting pytest
=================

In many cases the tests will run properly with ``py.test`` with no modifications, although the memory test case will not be executed.
``unittest`` test discovery is based on the presence of classes inherited from ``unittest.TestCase`` containing methods that begin with the string ``test``.
The simplest way to determine what changes are required is to run the test once using ``python`` and once using ``py.test``:

.. code-block:: shell

   $ python tests/statistics.py
   .........................
   ----------------------------------------------------------------------
   Ran 25 tests in 0.149s

   OK
   $ py.test tests/statistics.py
   ============================= test session starts ==============================
   platform darwin -- Python 2.7.11, pytest-2.8.5, py-1.4.31, pluggy-0.3.1
   rootdir: /Users/timj/work/lsstsw/src/afw/tests, inifile:
   collected 24 items

   tests/statistics.py ........................

   ========================== 24 passed in 0.64 seconds ===========================

Here it is clear that 24 tests ran instead of 25.
This is expected because the memory test case will not be "discovered" because it is hidden in the ``suite()`` definition.

If the test counts differ by more than one, or if they match, then more work may be required.
Possible issues are:

* A routine exists in the file with a ``test`` prefix but is not itself a test.
* The ``suite()`` does not list all the test classes that are in the file.
* Tests in a base class are being run inadvertently.

The issue of base classes needs some explanation.
In some test files, in order to avoid code duplication a base class is used defining the tests and then subclasses are used which override certain parameters.
Only the subclasses will be listed in the ``suite()``.
If the base class inherits from ``unittest.TestCase`` the tests in the base class will be executed even though it is likely that conditions are such that the tests will fail.
One solution to this problem is for the base class not to inherit from ``unittest.TestCase`` and to have the test subclasses themselves inherit from both the base class and the test base class.

It is also important that tests are skipped explicitly using the ``unittest`` skipping feature (such as raising ``unittest.SkipTest`` in the ``setup()`` phase, or using the ``@unittest.skipUnless`` decorator) rather than the test not being run without comment (which can be interpreted as a pass).
Skipping statistics are very important and large numbers of skipping tests can be indicative of a wider issue with the test suite.

One final comment is that the tests executed by pytest will not be in the same namespace as when they are run from the command line with Python.
If tests rely on knowing their own namespace they should use ``__name__`` rather than ``__main__``.

Memory Test
-----------

Every LSST test file includes the ``utilsTests.MemoryTestCase`` test for leaked resources in the C++ code.
This is the final test run from within each file and it relies on the ``utilsTests.init()`` method being called before any of the tests start.
In the current system this reset occurs when ``suite()`` is called before being passed to the test runner.
Pytest test discovery works by finding all the tests to be invoked first, and then running them so pytest must be configured to reset the memory leak counter before test classes are executed.
This can be done by adding the following to the top of the test file:

.. code-block:: python

   def setup_module(module):
       tests.init()

Making the memory test itself available to pytest can be achieved by adding it explicitly at the end of the test file as the final test class:

.. code-block:: python

   class MyMemoryTestCase(tests.MemoryTestCase):
       pass

This will then be run once the other tests in that file have been run.
As an additional protection, when the tests complete the leak counter is reset to allow new test files to start from a blank slate.
Despite that, it is safer to be explicit and call ``lsst.utils.tests.init()`` in the ``setup_module()`` function.

Testing Binaries
----------------

To enable a switch to pytest for all LSST testing, executable binaries must be tested from a Python wrapper.
The ``lsst.utils.tests`` package provides a simple means of doing this by providing a base test case class that can automatically discover binary executables and create a test for each one.
To enable this feature copy ``$UTILS_DIR/tests/testBinaries.py`` to the ``tests`` directory of your application.
In many cases this will just work, but it is also possible to restrict the testing to an explicit list of binaries.
For example:

.. code-block:: python

   import unittest
   import lsst.utils.tests as utilsTests

   class UtilsBinaryTester(utilsTests.BinariesTestCase):
       pass

   BINARIES = ("binary1", "binary2")
   UtilsBinaryTester.discover_tests(__file__, BINARIES)

   if __name__ == "__main__":
       unittest.main()

by explicitly listing the test binaries in a tuple.
The tuple of binaries can contain any executable that can be run from the shell and will return zero exit status if it works and non-zero if it fails.
The output from the test binary is captured.

In some cases, explicit tests should be written for each binary executable, such as when a test should be skipped if some precondition is not met.
In that case use can be made of the ``assertExecutable()`` method available in the ``BinariesTestCase`` class:

.. code-block:: python

   def testBinary(self):
       self.assertExecutable("binary1",
                             root_dir=os.path.dirname(__file__))

The optional second argument is required to allow the test to run regardless of the working directory from which the test is invoked.
In this case ``binary1`` would be located relative to the testing Python wrapper.

Cleaning up persistent state
----------------------------

Pytest is a test runner that is designed to be able to run tests from multiple files simultaneously.
This means that rather than each test file running in a separate process, pytest may run all of them sequentially within a single process.
This means that any persistent state defined in one test file must be reset so that it does not contaminate subsequent tests.
Currently, large test suites, such as those in ``afw`` and ``meas_astrom`` can give different answers depending on the order of the test files given to ``py.test``.
The pytest test runner integrated into ``sconsUtils`` will be designed explicitly to not guarantee the order in which test files will be executed.
When testing after migration to pytest please ensure that the tests run in a single process:

.. code-block:: shell

   $ py.test tests/*.py

and that the test file order does not matter:

.. code-block:: shell

   $ py.test `ls -r tests/*.py`

In many cases this will trigger unexpected failures in tests that work standalone or even in conjunction with some, not all, of the other tests.
These problems can be due to tests setting global state and not resetting it, or tests not correctly releasing resources (for example running out of file handles).
In extreme cases this could be indicative of memory corruption issues in the C++ code.

Remove the suites
-----------------

Once the tests have been modified to support standard test discovery the suite handling boilerplate can be removed and replaced with:

.. code-block:: python

   if __name__ == "__main__":
       unittest.main()

Whilst it will then be possible to run the tests using ``python`` directly, the advice is that tests should be executed by ``py.test`` if at all possible, to emulate the CI environment.
