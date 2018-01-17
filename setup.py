# Copyright (c) 2018 Marco Giusti

from setuptools import setup


with open('README') as fd:
    long_description = fd.read()

setup(
    name='adsdb3',
    version='0.1.0',
    description='Python 3 Advantage database interface',
    long_description=long_description,
    author='Marco Giusti',
    author_email='marco.giusti@posteo.de',
    url='https://github.com/marcogiusti/adsdb3',
    license='MIT',
    package_dir={'': 'src'},
    py_modules=['adsdb3'],
    setup_requires=['cffi>=1.0.0'],
    cffi_modules=['src/ace_build.py:ffibuilder'],
    install_requires=['cffi>=1.0.0'],
    extras_require={
        'dev': [
            'coverage',
            'hypothesis',
            'pep8',
            'pyflakes',
            'tox',
            'wheel'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Database'
    ]
)
