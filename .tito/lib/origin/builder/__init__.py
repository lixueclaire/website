"""
Code for building Origin
"""

import sys
import json

from tito.common import (
    get_latest_commit,
    get_latest_tagged_version,
    check_tag_exists,
    run_command,
    find_spec_file,
    get_spec_version_and_release,
    munge_specfile
)

from tito.builder import Builder

class OriginBuilder(Builder):
    """
    builder which defines 'commit' as the git hash prior to building

    Used For:
        - Packages that want to know the commit in all situations
    """

    def _get_rpmbuild_dir_options(self):
        git_hash = get_latest_commit()
        cmd = '. ./hack/common.sh ; echo $(os::build::ldflags)'
        ldflags = run_command("bash -c '{0}'".format(cmd))

        return ('--define "_topdir %s" --define "_sourcedir %s" --define "_builddir %s" '
                '--define "_srcrpmdir %s" --define "_rpmdir %s" --define "ldflags %s" '
                '--define "commit %s" ' % (
                    self.rpmbuild_dir,
                    self.rpmbuild_sourcedir, self.rpmbuild_builddir,
                    self.rpmbuild_basedir, self.rpmbuild_basedir,
                    ldflags, git_hash))

    def _setup_test_specfile(self):
        if self.test and not self.ran_setup_test_specfile:
            # If making a test rpm we need to get a little crazy with the spec
            # file we're building off. (note that this is a temp copy of the
            # spec) Swap out the actual release for one that includes the git
            # SHA1 we're building for our test package:
            sha = self.git_commit_id[:7]
            fullname = "{0}-{1}".format(self.project_name, self.display_version)
            munge_specfile(
                self.spec_file,
                sha,
                self.commit_count,
                fullname,
                self.tgz_filename,
            )
            # Custom Openshift v3 stuff follows, everything above is the standard
            # builder
            cmd = '. ./hack/common.sh ; echo $(os::build::ldflags)'
            ldflags = run_command("bash -c '{0}'".format(cmd))
            print("LDFLAGS::{0}".format(ldflags))
            update_ldflags = \
                    "sed -i 's|^%%global ldflags .*$|%%global ldflags {0}|' {1}".format(
                        ' '.join([ldflag.strip() for ldflag in ldflags.split()]),
                        self.spec_file
                    )
            # FIXME - output is never used
            output = run_command(update_ldflags)

            # Add bundled deps for Fedora Guidelines as per:
            # https://fedoraproject.org/wiki/Packaging:Guidelines#Bundling_and_Duplication_of_system_libraries
            provides_list = []
            with open("./Godeps/Godeps.json") as godeps:
                depdict = json.load(godeps)
                for bdep in [
                    (dep[u'ImportPath'], dep[u'Rev'])
                    for dep in depdict[u'Deps']
                ]:
                    provides_list.append(
                        "Provides: bundled(golang({0})) = {1}".format(
                            bdep[0],
                            bdep[1]
                        )
                    )
            update_provides_list = \
                "sed -i 's|^### AUTO-BUNDLED-GEN-ENTRY-POINT|{0}|' {1}".format(
                    '\\n'.join(provides_list),
                    self.spec_file
                )
            print(run_command(update_provides_list))

            self.build_version += ".git." + \
                str(self.commit_count) + \
                "." + \
                str(self.git_commit_id[:7])
            self.ran_setup_test_specfile = True

    def _get_build_version(self):
        """
        Figure out the git tag and version-release we're building.
        """
        # Determine which package version we should build:
        build_version = None
        if self.build_tag:
            build_version = self.build_tag[len(self.project_name + "-"):]
        else:
            build_version = get_latest_tagged_version(self.project_name)
            if build_version is None:
                if not self.test:
                    error_out(["Unable to lookup latest package info.",
                            "Perhaps you need to tag first?"])
                sys.stderr.write("WARNING: unable to lookup latest package "
                    "tag, building untagged test project\n")
                build_version = get_spec_version_and_release(self.start_dir,
                    find_spec_file(in_dir=self.start_dir))
            self.build_tag = "v{0}".format(build_version)

        if not self.test:
            check_tag_exists(self.build_tag, offline=self.offline)
        return build_version

# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:textwidth=0:
