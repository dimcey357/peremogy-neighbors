from telegram.ext import BaseFilter
import re


class MyFilters(BaseFilter):
    """Custom filters"""

    @staticmethod
    def call_err(message):
        return 'error' == message.text

    @staticmethod
    def integers(message):
        if message.text:
            pattern = r'^[0-9]+$'
            found = re.findall(pattern, message.text)
            return found if found else False

    @staticmethod
    def flood(message):
        pattern = r'\bфлуд\w{,4}\b|\bбубнил\w{,4}\b'
        if message.text:
            found = re.findall(pattern, message.text, flags=re.IGNORECASE)
            return found if found else False

    @staticmethod
    # block forwarding msg from specific users
    def open_data_ua_bot(message):
        if message.forward_from:
            return message.forward_from.id == 215115043


filt_integers = MyFilters().integers
filt_call_err = MyFilters().call_err
filt_flood = MyFilters().flood
# filt_open_data_ua_bot = MyFilters().open_data_ua_bot


class FilterBlock(BaseFilter):
    def filter(self, message):
        pattern = r'\bху[е,й,я]\w{,4}\b|\bп[і,ы,и]зда\w{,4}\b'
        if message.text:
            found = re.findall(pattern, message.text, flags=re.IGNORECASE)
            return found if found else False

block_filter = FilterBlock()
