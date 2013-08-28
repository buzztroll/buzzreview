import getpass
import buzzreview.gerrit


def print_review(r, details=False):
    print '--------'
    print r.number
    print '--------'
    print r.subject
    print r.url
    print r.owner
    print str(r.created_on) + "  -- " + str(r.last_updated)
    diffs = r.git_differences()
    print "Total files touched %d" % len(diffs)
    line_changes = sum([len(d.new_lines) for d in diffs])
    deleted_lines = sum([len(d.deleted_lines) for d in diffs])
    print "Line changes +%d, -%d" % (line_changes, deleted_lines)
    print "Coverage:"
    total = 0
    for d in diffs:
        if details:
            print d.file_name
            print "\t%s" % (str(d.uncovered))
            print "\t%d" % (len(d.uncovered))
        total += len(d.uncovered)
    print "Total not covered: %d" % total
    print "Percent not covered %3.2f" % (float(total) / float(line_changes) * 100.0)
    print ""

def main():
    # --help
    # --reviewier
    # --branch
    # --all (all reviews)
    # --spectic
    # --basedir
    reviews = buzzreview.gerrit.get_gerrit_info(branch='master',
                                                approvers=[getpass.getuser()])

    for r in reviews:
        r.checkout()
        print_review(r)
    print len(reviews)


