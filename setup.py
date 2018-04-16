#!/usr/bin/env python
"""Treadmill setup.py."""

# pip 10.0 moved req to _internal. Need to find better solution, changing
# for now so that build pass.
try:
    import pip.req as pip_req
except ImportError:
    import pip._internal.req as pip_req


def _read_requires(filename):
    reqs = []
    for inst_req in pip_req.parse_requirements(filename, session='no session'):
        req = str(inst_req.req)
        if not inst_req.match_markers():
            print('Skipping %r: %r => False' % (req, inst_req.markers))
            continue
        reqs.append(str(inst_req.req))
    return reqs


from setuptools import setup  # pylint: disable=wrong-import-position


setup(
    version='3.7',
    install_requires=_read_requires('requirements.txt'),
    setup_requires=_read_requires('test-requirements.txt')
)
