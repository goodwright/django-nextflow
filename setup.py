from setuptools import setup

with open("README.md") as f:
    long_description = f.read()

setup(
    name="django_nextflow",
    version="0.1.0",
    description="A django library for running Nextflow pipelines and storing their result.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/samirelanduk/django-nextflow",
    author="Sam Ireland",
    author_email="sam@goodwright.com",
    license="GPLv3+",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 3.1",
        "Framework :: Django :: 3.2",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Framework :: Django",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="django nextflow pipeline bioinformatics",
    packages=["django_nextflow"],
    include_package_data=True,
    python_requires="!=2.*, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*",
    install_requires=["nextflow"]
)
