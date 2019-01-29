from setuptools import find_packages, setup


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="drf-jsonapi",
    use_scm_version=True,
    license="MIT",
    description="OpenSource Django JSONAPI Library",
    long_description=readme(),
    keywords="django jsonapi",
    author="Vacasa, LLC",
    author_email="opensource@vacasa.com",
    url="https://github.com/vacasa/drf-jsonapi",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    install_requires=["django", "djangorestframework"],
    setup_requires=["setuptools_scm", "setuptools_scm_git_archive"],
    zip_safe=False,
)
