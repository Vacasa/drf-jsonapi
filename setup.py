from setuptools import find_packages, setup


def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='drf-jsonapi',
    version='0.1.0',
    license='MIT',
    description='OpenSource Django JSONAPI Library',
    long_description=readme(),
    keywords='django jsonapi',
    author='Vacasa, LLC',
    author_email='opensource@vacasa.com',
    url='https://github.com/vacasa/django-jsonapi-lib',
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    install_requires=[
        'django',
        'djangorestframework',
        'drf-nested-routers',
        'django-filter',
        'drf-yasg',
    ],
    zip_safe=False
)
