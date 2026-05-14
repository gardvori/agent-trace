from setuptools import setup, find_packages

setup(
    name="agent-trace",
    version="0.1.0",
    description="Lightweight observability CLI for AI agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="gardvori",
    url="https://github.com/gardvori/agent-trace",
    py_modules=["agent_trace"],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "agent-trace=agent_trace:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Debuggers",
    ],
)
