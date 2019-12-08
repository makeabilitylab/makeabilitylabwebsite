"""
Hosts general utility functions for Makeability Lab Django website
"""
import re

# helper function to correctly capitalize a string, specify words to not capitalize in the articles list
# from: https://stackoverflow.com/a/3729957
# Note: this code written by J. Gilkeson and needs to be cleaned up (and/or removed if no longer needed)
def capitalize_title(s, exceptions):
    word_list = re.split(' ', s)       # re.split behaves as expected
    final = [word_list[0].capitalize()]
    for word in word_list[1:]:
        final.append(word if word in exceptions else word.capitalize())
    return " ".join(final)

#Standard list of words to not capitalize in a sentence
articles = ['a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'is', 'of', 'on', 'or', 'nor', 'the', 'to', 'up', 'yet']