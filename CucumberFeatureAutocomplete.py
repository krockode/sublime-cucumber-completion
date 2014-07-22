import re
import os
import logging

import sublime
import sublime_plugin

try:
    from itertools import izip_longest as zip_longest
except:
    from itertools import zip_longest

thing = ''
step_def_urls = []
ruby_regexp = re.compile(r'[/"]\(?\^?(.*?)\$?[/"]\)? do(.*)')
groovy_regexp = re.compile(r"[/'\"]\^?(.*?)\$?[/'\"]\) \{ (.*?) ?->")
step_def_regexps = {'groovy': groovy_regexp, 'rb': ruby_regexp}
suffixes = ['steps.{0}'.format(k) for k in step_def_regexps.keys()]
step_folders = []
log = logging.getLogger(__name__)

background_completion = (
    "Background template",
    """Feature: $1<enter feature title>
    In order $2...
    As a ...
    I want

    Background: $3<enter background title - applies to every Scenario>
        Given $4

    Scenario: $5<enter scenario title>
        When $6""")
scenario_completion = (
    "Scenario template",
    """Scenario: $1<enter scenario title>
    When $2""")

whens = ['Given', 'When', 'Then', 'And', 'But', '*']


class CucumberFeatureAutocomplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        # Only trigger within feature files

        file_name = view.file_name()
        if (not file_name):
            file_name = ''
        if (view.score_selector(0, 'text.gherkin.feature') == 0 and
                not file_name.endswith('.feature')):
            return []
        line = view.substr(sublime.Region(view.line(locations[0]).a,
                           view.word(locations[0]).begin()))
        line_len = view.line(locations[0]).b - view.line(locations[0]).a
        if (not line.strip()):
            indent = self.calculate_step_indent(view, locations[0])
            log.debug("indent: {0} len: {1} line_len: {2}".format(
                      indent, len(line), line_len))
            padding = " " * (indent - line_len)
            completions = None
            if locations[0] < 20:
                completions = [background_completion, scenario_completion]
            else:
                completions = [scenario_completion]
            completions += [(when, padding + when + " ") for when in whens]
            return completions
        else:
            completion_flags = [
                sublime.INHIBIT_WORD_COMPLETIONS |
                sublime.INHIBIT_EXPLICIT_COMPLETIONS]
            if not step_folders:
                step_completions = self.find_completions(view.window().folders())
            else:
                step_completions = self.find_completions(step_folders)
            completions = [(c, c) for c in step_completions]# + completion_flags
            return completions

    def find_completions(self, base_folders):
        """Find possible completions from the given base folders
        """
        regex_and_params = self.find_step_defs(base_folders)
        regex_and_params = sorted(regex_and_params, key=lambda tup: tup[0])
        return [self.create_completion_text(*completion)
                for completion in regex_and_params]

    def calculate_step_indent(self, view, location):
        """Search for step indent to use for the current file

        Search lines from the cursor position back to the start of the file
        to determine the indent to use.
        """
        regions = view.lines(sublime.Region(0, location))[::-1]
        for region in regions:
            line = view.substr(region)
            if any([line.strip().startswith(when) for when in whens]):
                return len(line) - len(line.lstrip())
        return 8  # default

    def find_step_defs(self, base_folders):
        step_matches = []
        for step_file, step_file_name in self.find_step_files(base_folders):
            for key in step_def_regexps:
                if step_file_name.endswith(key):
                    step_def_regexp = step_def_regexps.get(key)
                    for line in step_file:
                        m = step_def_regexp.search(line)
                        if m:
                            step_matches.append(m.groups())
        return step_matches

    def find_step_files(self, base_folders):
        for base in base_folders:
            for (path, dirs, files) in os.walk(base):
                for file_name in files:
                    if any(file_name.lower().endswith(s) for s in suffixes):
                        if not (path in step_folders):
                            step_folders.append(path)
                        log.debug("found: " + file_name)
                        with open(os.path.join(path, file_name)) as f:
                            yield f, file_name

    def create_completion_text(self, completion, fields):
        """Create human readable text from the step regular expression

        Take the step regex, and the parameter names for the step and zip
        them together
        """
        fields = fields.replace('|', '').replace('$', '$$')
        params = [x.strip() for x in re.split(',', fields)]
        field_chunks = [re.split(' ', x)[-1] for x in params]
        unbraced_chunks = re.split('(\([^?:][^())]*\))', completion)
        try:
            for i in range(0, len(unbraced_chunks)):
                if i%2 == 1 and not re.match(r'\([\w \|]+\)', unbraced_chunks[i]):
                    unbraced_chunks[i] = '('+field_chunks[(i-1)//2]+')'
            return "".join(map("".join, unbraced_chunks))
        except:
            log.exception("failed completion: {0} fields: {1}".format(
                completion, fields))
            return completion

class CucumberCompletionResetStepFoldersCommand(sublime_plugin.WindowCommand):
    
    def __init__(self, window):
        sublime_plugin.WindowCommand.__init__(self, window)

    def run(self):
        global step_folders
        step_folders = []