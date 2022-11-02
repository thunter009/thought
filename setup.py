#!/usr/bin/env python

"""The setup script."""

from setuptools import find_namespace_packages, setup

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

setup(
    extras_require={
        "dev": [
            "bump2version",
            "wheel",
            "watchdog",
            "pylint",
            "flake8",
            "pdbpp",
            "tox",
            "coverage",
            "sphinx",
            "twine",
            "autopep8",
            "ipykernel",
            "black",
            "pre-commit",
        ]
    },
    author="Tom Hunter",
    author_email="tom@hunter.com",
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Notion CLI using notion-py library and Click",
    entry_points={
        "console_scripts": [
            "thought=thought.cli:cli",
        ],
    },
    install_requires=[
        "click",
        "python-dotenv",
        "notion",
        "pandas",
        "recordlinkage",
        "requests-oauthlib",
        "pytoml",
        "requests",
        "notion-client",
        "regex",
    ],
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="thought",
    name="thought",
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    setup_requires=[],
    test_suite="tests",
    tests_require=[],
    url="https://github.com/thunter009/thought",
    version="0.1.0",
    zip_safe=False,
)
