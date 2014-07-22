from os import listdir, path

import sublime
import sublime_plugin

from CucumberFeatureAutocomplete import CucumberFeatureAutocomplete

completer = CucumberFeatureAutocomplete()
ex = 'examples'


def test_examples():
    """test all example step definitions found in the examples directory"""
    tests = [d for d in listdir(ex) if path.isdir(path.join(ex, d))]
    for d in tests:
        yield check_examples, d


def check_examples(d):
    message = "expectations failed for completions in {0}; found: '{1}'"
    test_dir = path.join(ex, d)
    expected = set(open('{0}.expected'.format(test_dir)).read().splitlines())
    found = set(completer.find_completions([test_dir]))
    assert expected == found, message.format(d, "', '".join(found))


def test_splitting_regex_by_no_groups():
    assert completer.create_completion_text("no groups", '') == "no groups"


def test_splitting_regex_by_groups():
    chunks = completer.create_completion_text('The customers name is (.*)', 'group1')
    assert 'The customers name is (group1)' == chunks
    chunks = completer.create_completion_text('Mrs (.*) is a customer', 'group1')
    assert 'Mrs (group1) is a customer' == chunks
    chunks = completer.create_completion_text('(Mr|Mrs|Ms) (.*) is a customer', 'group1, group2')
    assert '(Mr|Mrs|Ms) (group2) is a customer' == chunks


def test_splitting_regex_ignores_outer_braces():
    chunks = completer.create_completion_text('More (braces (arent)) groups', 'group1')
    assert 'More (braces (group1)) groups' == chunks

def test_splitting_regex_non_catching_groups():
    chunks = completer.create_completion_text('This sentence contains(?: non catched (.*)) group', 'group1')
    assert 'This sentence contains(?: non catched (group1)) group'