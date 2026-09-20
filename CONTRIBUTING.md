Contributing
============

Keep changes small and keep cmp1 stable.

Before Sending a Change
-----------------------

* Read spec/cmp-0001.md
* Check vectors.json
* Run the test suite

Run tests with:

    python -m unittest discover -s tests -v

Format Changes
--------------

A change to a CMP 1 rule needs a new CMP ID.
Do not change existing cmp1 behavior in place.

Tests
-----

* Add a test for changed behavior
* Update vectors.json when format behavior changes
* Keep existing vectors passing

Code
----

* Use simple Python
* Keep functions small
* Keep comments short
* Add comments only when the code is not clear
* Avoid new dependencies when possible
