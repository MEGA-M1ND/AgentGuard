"""Setup script for AgentGuard Python SDK"""
from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="agentguard",
    version="0.1.0",
    author="AgentGuard Team",
    author_email="support@agentguard.dev",
    description="Python SDK for AgentGuard - Identity + Permissions + Audit Logs for AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/agentguard",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "requests>=2.31.0",
    ],
)
