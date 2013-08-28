import getpass
import buzzreview.gerrit
import optparse

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
    percent = 0.0
    if line_changes != 0:
        percent = (float(total) / float(line_changes) * 100.0)
    print "Percent not covered %3.2f" % percent
    print ""


def main():
    parser = optparse.OptionParser(usage="usage: %prog [options]",
                                   version="%prog 0.1")
    parser.add_option("-V", "--verbose",
                      dest="verbose",
                      action="store_true",
                      default=False,
                      help="Show more details.")
    parser.add_option("-J", "--no-jenkins",
                      dest="need_jenkins",
                      action="store_false",
                      default=True,
                      help="Do not insist that it passed jenkins.")
    parser.add_option("-b", "--branch",
                      dest="branch",
                      default=None,
                      help="The branch to check.  No onther branch will be reviewed.")
    parser.add_option("-p", "--project",
                      dest="project",
                      default='glance',
                      help="The project to check reviews on.  Default is glance")
    parser.add_option("-n", "--number",
                      dest="numbers",
                      action="append",
                      default=None,
                      help="The specific bug number to review.  This can be used multiple times.  The defaiult is all.",)
    parser.add_option("-r", "--reviewer",
                      dest="reviewer",
                      action="append",
                      default=None,
                      help="Ignore all reviews if this reviewer has already commented.  The default is the current unix user.",)
    parser.add_option("-d", "--basedir",
                      dest="basedir",
                      default=None,
                      help="The directory under which all the code will be checked out, the default is the users home directory.",)
    (options, args) = parser.parse_args()

    # --reviewier
    reviews = buzzreview.gerrit.get_gerrit_info(
        branch=options.branch,
        approvers=options.reviewer,
        basedir=options.basedir,
        need_jenkins=options.need_jenkins,
        project=options.project)


    for r in reviews:
        if options.numbers and r.number not in options.numbers:
            continue
        r.checkout()
        print_review(r, details=options.verbose)
    print len(reviews)


