from setuptools import setup, find_packages
from event_queue import __version__, __author__, __email__

setup(
    name='django-event-queue',
    version=__version__,
    packages=find_packages(),
    install_requires=[
        'pika==0.11.0'
    ],
    url='https://github.com/ducminhgd/event-queue',
    license='',
    author=__author__,
    author_email=__email__,
    description='Python Event Queue'
)
