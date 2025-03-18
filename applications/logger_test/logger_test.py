import logging
import unipi.logging

unipi.logging.init_logger()


class MyClass:

    def __init__(self):
        self.logger = logging.getLogger(__class__.__name__)


def main():

    my_class = MyClass()
    my_class.logger.info('hello')


if __name__ == '__main__':
    main()
