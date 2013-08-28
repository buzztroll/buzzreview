import coverage
import getpass
import os
import pygit2
import shutil
import subprocess
import json
from datetime import datetime


class ReviewFile(object):
    def __init__(self, hunk, cov, basedir):
        self.file_name = hunk.new_file_path
        self.hunk = hunk
        self.new_lines, self.deleted_lines = self._get_new_lines()
        coverage_dir = os.path.join(basedir, 'glance')
        self.total_missing_lines = self._get_uncovered_lines(cov, coverage_dir)
        self.uncovered = list(set(self.new_lines) & set(self.total_missing_lines))
        self.uncovered.sort()

    def _get_new_lines(self):
        new_lines = []
        deleted_lines = []
        for h in self.hunk.hunks:
            line_index = 0
            for l in h.lines:
                if l[0] == u'+':
                    new_lines.append(h.new_start + line_index)
                elif l[0] == u'-':
                    deleted_lines.append(h.new_start + line_index)
                line_index += 1
        return new_lines, deleted_lines

    def _get_uncovered_lines(self, cov, basedir):
        hunk_path = os.path.join(basedir, self.hunk.new_file_path)
        missing_list = cov.analysis2(hunk_path)
        return missing_list[3]


def check_jenkins_rejection(approvals):
    for a in approvals:
        if a['by']['username'] == 'jenkins':
            return a['value'] > 0
    return False


def check_approvers(review_approval, approvers):
    for a in review_approval:
        if a['by']['username'] in approvers:
            return True
    return False


class PatchSubmission(object):
    def __init__(self, review, basedir):
        self._raw_review = review
        self.subject = review['subject']
        self.last_updated = datetime.fromtimestamp(review['lastUpdated'])
        self.created_on = datetime.fromtimestamp(review['createdOn'])
        self.ref = review['currentPatchSet']['ref']
        self.url = review['url']
        self.number = review['number']
        self.project = review['project']
        self.owner = review['owner']['username']
        self.git_cmd = ('git fetch https://review.openstack.org/%(project)s %(ref)s'
                        ' && git checkout FETCH_HEAD' % self.__dict__)
        self.dir = os.path.join(basedir, 'review%s' % self.number)
        self.review_file = os.path.join(self.dir, 'review.txt')


    def _test_checkout(self):
        if not os.path.exists(self.dir):
            return True

        if not os.path.exists(self.review_file):
            return True

        r_json = json.load(open(self.review_file, 'r'))
        stored_review = PatchSubmission(r_json, '/tmp/')
        if stored_review.last_updated != self.last_updated:
            return True

        return False

    def _execute(self, cmd):
        self._execute_and_print(cmd)

    def _execute_and_print(self, cmd):
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rc = p.poll()
        print cmd
        while rc is None:
            #print p.stderr.readline()
            print p.stdout.readline()
            rc = p.poll()
        print rc
        stdout, stderr = p.communicate()
        print stdout
        print stderr

    def checkout(self):
        if not self._test_checkout():
            return
        try:
            shutil.rmtree(self.dir)
        except:
            pass

        os.mkdir(self.dir)
        os.chdir(self.dir)
        git_checkout = 'git clone https://github.com/%s.git' % (self.project)
        self._execute(git_checkout)
        os.chdir(os.path.join(self.dir, 'glance'))
        self._execute(self.git_cmd)
        self._execute('git checkout -b review')
        self._test()
        with open(self.review_file, 'w') as fp:
            json.dump(self._raw_review, fp)

    def _test(self):
        cmd = 'tox -epy27 -- --with-coverage'
        self._execute_and_print(cmd)

    def git_differences(self):
        _git = os.path.join(self.dir, 'glance/.git')
        _coverage = os.path.join(self.dir, 'glance/.coverage')
        cov = coverage.coverage(_coverage)
        cov.load()

        if not os.path.isdir(_git):
            raise IOError(".git does not exist in the directory %s" % _git)
        repo = pygit2.Repository(_git)
        commit = repo.head.get_object()
        if len(commit.parents) != 1:
            raise Exception('Problem, many parents')
        parent = commit.parents[0]
        diff = parent.tree.diff_to_tree(commit.tree)

        altered_files = []
        for hunk in diff:
            af = ReviewFile(hunk, cov, self.dir)
            altered_files.append(af)
        return altered_files


def _get_from_gerrit(hostname='review.openstack.org', port=29418,
                     username=None, branch=None, approvers=None,
                     basedir=None):
    if username is None:
        username = getpass.getuser()

    if basedir is None:
        basedir = os.path.expanduser('~/')

    ssh_cmd = ('ssh %s@%s -p %d gerrit query'
                '" status:open project:openstack/glance" --format JSON'
                 ' --current-patch-set' % (username, hostname, port))

    p = subprocess.Popen([ssh_cmd], shell=True, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = p.stdout
    reviews = []
    for line in stdout.readlines():
        review = json.loads(line)
        if 'status' not in review:
            continue
        if review['status'] == 'WORKINPROGRESS':
             continue

        # skip anything that jenkins did not approve
        if 'approvals' not in review['currentPatchSet']:
            continue
        if not check_jenkins_rejection(review['currentPatchSet']['approvals']):
            continue

        if approvers and check_approvers(review['currentPatchSet']['approvals'],
                                         approvers):
            continue

        if branch and review['branch'] != branch:
            continue

        reviews.append(PatchSubmission(review, basedir))

    return reviews

def get_gerrit_info(branch=None, approvers=None):
    return _get_from_gerrit(branch=branch, approvers=approvers)