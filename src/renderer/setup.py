#!/usr/bin/env python3
"""
Setup script for the datasheet-renderer package.
"""

from setuptools import setup, find_packages

setup(
    name="datasheet-renderer",
    version="0.1.0",
    description="Renderer for Datasheets for Datasets templates",
    author="Bridge2AI Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pyyaml",
        "jinja2",
        "markdown",
        "weasyprint",
        "python-docx",
        "fpdf",
        "pandas",
        "openpyxl",
    ],
    entry_points={
        "console_scripts": [
            "datasheet-renderer=renderer.main:main",
            "docx-extract=renderer.simple_extractor:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)