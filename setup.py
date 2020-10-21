"""pyramid_caching_api installation script.
"""
import os

from setuptools import setup
from setuptools import find_packages

HERE = os.path.abspath(os.path.dirname(__file__))
long_description = description = "Lightweight cache manager for Pyramid and dogpile"
with open(os.path.join(HERE, "README.md")) as fp:
    long_description = fp.read()

install_requires = [
    "pyramid",
    "dogpile.cache",
]
tests_require = ["pytest"]
testing_extras = tests_require + []

setup(
    name="pyramid_caching_api",
    version="0.0.2",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Intended Audience :: Developers",
        "Framework :: Pyramid",
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="web pyramid dogpile",
    py_modules=["pyramid_caching_api"],
    author="Jonathan Vanasco",
    author_email="jonathan@findmeon.com",
    url="https://github.com/jvanasco/pyramid_caching_api",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        "testing": testing_extras,
    },
    test_suite="tests",
)
