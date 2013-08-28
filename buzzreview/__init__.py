import os
import sys

import coverage
import pygit2


class GitDiffFile(object):
    def __init__(self, hunk, basedir):
        self.file_name = hunk.new_file_path
        self.hunk = hunk
        self.new_lines = self._get_new_lines()

    def _get_new_lines(self):
        new_lines = []
        for h in self.hunk.hunks:
            line_index = 0
            for l in h.lines:
                if l[0] == u'+':
                    new_lines.append(h.new_start + line_index)
                line_index += 1
        return new_lines


class AlteredFile(object):
    def __init__(self, hunk, cov, basedir):
        self.file_name = hunk.new_file_path
        self.hunk = hunk
        self.new_lines = self._get_new_lines()
        self.total_missing_lines = self._get_uncovered_lines(cov, basedir)
        self.missing = list(set(self.new_lines) & set(self.total_missing_lines))
        self.missing.sort()

    def _get_new_lines(self):
        new_lines = []
        for h in self.hunk.hunks:
            line_index = 0
            for l in h.lines:
                if l[0] == u'+':
                    new_lines.append(h.new_start + line_index)
                line_index += 1
        return new_lines

    def _get_uncovered_lines(self, cov, basedir):
        hunk_path = os.path.join(basedir, self.hunk.new_file_path)
        missing_list = cov.analysis2(hunk_path)
        return missing_list[3]

def get_altered_files(working_dir):
    _git = os.path.join(working_dir, '.git')
    _coverage = os.path.join(working_dir, '.coverage')
    if not os.path.isdir(_git):
        raise IOError(".git does not exist in the directory %s" % _git)
    if not os.path.exists(_coverage):
        raise IOError(
            ".coverage does not exists in the directory %s" % _coverage)

    repo = pygit2.Repository(_git)
    cov = coverage.coverage(_coverage)
    cov.load()

    return list(find_missing_appear(cov, repo))


def find_missing_appear(cov, repo):
    commit = repo.head.get_object()
    for parent in commit.parents:
        diff = parent.tree.diff_to_tree(commit.tree)
        for hunk in diff:
            altered_file = AlteredFile(hunk, cov, repo.workdir)
            yield altered_file


FAIL = '\033[91m'
ENDC = '\033[0m'


def report(cov, repo):
    new_lines = 0
    for altered_file in find_missing_appear(cov, repo):
        print altered_file.file_name
        print "\t %s" % str(list(altered_file.missing))
        new_lines += len(altered_file.new_lines)

    print "%d new files.  %d new lines" % (len(altered_file), new_lines)


def main():
    if len(sys.argv) > 1:
        target_repository = sys.argv[1]
    else:
        target_repository = os.getcwd()

    _git = os.path.join(target_repository, '.git')
    _coverage = os.path.join(target_repository, '.coverage')
    if not os.path.isdir(_git):
        raise IOError(".git does not exist in the directory %s" % _git)
    if not os.path.exists(_coverage):
        raise IOError(
            ".coverage does not exists in the directory %s" % _coverage)

    repo = pygit2.Repository(_git)
    cov = coverage.coverage(_coverage)
    cov.load()
    report(cov, repo)


if __name__ == '__main__':
    main()
