from distutils.core import setup

setup(
    name='django-inline-changelist',
    version='0.1-dev',
    test_suite='inline_changelist.test',
    packages=['inline_changelist'],
    install_requires=[],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.rst').read(),
)
