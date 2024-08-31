from setuptools import setup, find_packages

setup(
    name="pbir-utils",
    version="0.4.0",
    description="A tool for managing Power BI Enhanced Report Format (PBIR) projects",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/akhilannan/PBIR-Utils",
    author="Akhil Ashok",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "dash",
        "plotly",
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
