#!/usr/bin/python

from setuptools import find_packages, setup

setup(
    name="izanami",
    install_requires=[
        "mitama",
        "GitPython"
    ],
    extra_requires={"develop": ["unittest", "flake8", "isort", "black"]},
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    packages=find_packages(),
    package_data={
        "izanami": [
            "templates/*.html",
            "templates/**/*.html",
            "static/*",
        ]
    }
)
