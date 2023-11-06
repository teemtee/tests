#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Description: Example of a beakerlib library
#   Author: Petr Splichal <psplicha@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   library-prefix = file
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

true <<'=cut'
=pod

=head1 NAME

example/file - example of a beakerlib library

=head1 DESCRIPTION

This is a trivial example of a BeakerLib library. It's main goal
is to provide a minimal template which can be used as a skeleton
when creating a new library. It implements function fileCreate().
Please note, that all library functions must begin with the same
prefix which is defined at the beginning of the library.

=cut

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   Variables
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

true <<'=cut'
=pod

=head1 VARIABLES

Below is the list of global variables. When writing a new library,
please make sure that all global variables start with the library
prefix to prevent collisions with other libraries.

=over

=item fileFILENAME

Default file name to be used when no provided ('foo').

=back

=cut

fileFILENAME="foo"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   Functions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

true <<'=cut'
=pod

=head1 FUNCTIONS

=head2 fileCreate

Create a new file, name it accordingly and make sure (assert) that
the file is successfully created.

    fileCreate [filename]

=over

=item filename

Name for the newly created file. Optionally the filename can be
provided in the FILENAME environment variable. When no file name
is given 'foo' is used by default.

=back

Returns 0 when the file is successfully created, non-zero otherwise.

=cut

fileCreate() {
    local filename
    filename=${1:-$FILENAME}
    filename=${filename:-$fileFILENAME}
    rlRun "touch '$filename'" 0 "Creating file '$filename'"
    rlAssertExists "$filename"
    return $?
}

true <<'=cut'
=pod

=head1 FUNCTIONS

=head2 randomFileCreate

Create a random file

    randomFileCreate

=over

=back

Returns 0 when the file is successfully created, non-zero otherwise.

=cut

randomFileCreate() {
    source ${BASH_SOURCE%/*}/../scripts/random_file.sh
    return $?
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   Execution
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

true <<'=cut'
=pod

=head1 EXECUTION

This library supports direct execution. When run as a task, phases
provided in the PHASE environment variable will be executed.
Supported phases are:

=over

=item Create

Create a new empty file. Use FILENAME to provide the desired file
name. By default 'foo' is created in the current directory.

=item Test

Run the self test suite.

=back

=cut

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   Verification
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   This is a verification callback which will be called by
#   rlImport after sourcing the library to make sure everything is
#   all right. It makes sense to perform a basic sanity test and
#   check that all required packages are installed. The function
#   should return 0 only when the library is ready to serve.

fileLibraryLoaded() {
    if rpm=$(rpm -q coreutils); then
        rlLogDebug "Library example/file running with $rpm"
        return 0
    else
        rlLogError "Package coreutils not installed"
        return 1
    fi
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   Authors
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

true <<'=cut'
=pod

=head1 AUTHORS

=over

=item *

Petr Splichal <psplicha@redhat.com>

=back

=cut
