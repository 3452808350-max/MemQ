#!/usr/bin/env python3
"""
setup.py for DSS Browser Search CLI

安装方法：
    pip install -e /home/kyj/.openclaw/workspace/dss_modules

或者：
    cd /home/kyj/.openclaw/workspace/dss_modules
    pip install -e .
"""

from setuptools import setup, find_packages

setup(
    name="dss-browser-search",
    version="1.0.0",
    author="DSS Team",
    description="DSS浏览器自动化搜索CLI - 使用Playwright搜索Seeking Alpha、Yahoo Finance、Google Finance和财经新闻",
    long_description=open("README_browser_search.md").read() if __import__('os').path.exists("README_browser_search.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/HKUDS/CLI-Anything",
    py_modules=["browser_search_cli"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0.0",
        "playwright>=1.40.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "browser-search=browser_search_cli:main",
            "dss-search=browser_search_cli:main",
        ],
    },
    zip_safe=False,
)